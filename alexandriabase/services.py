'''
Created on 07.02.2018

@author: michael
'''
import codecs
import logging
import os
import re
import shutil
import struct
import sys
import tempfile

from _io import BytesIO
from math import ceil
from subprocess import call

from injector import inject, provider, ClassProvider, singleton, Module

from PIL import ImageFont, ImageDraw, Image

from PyPDF2.generic import DictionaryObject, readObject
from PyPDF2.merger import PdfFileMerger
from PyPDF2.pdf import ContentStream, PdfFileReader
from PyPDF2.utils import readNonWhitespace, b_, PdfReadError

from reportlab.platypus.paragraph import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, inch
from reportlab.platypus.flowables import Image as PdfImage

from sqlalchemy.sql.expression import text, update, select

from alexandriabase import _, baseinjectorkeys, fontdir
from alexandriabase.base_exceptions import NoSuchEntityException
from alexandriabase.daos import CURRENT_VERSION, REGISTRY_TABLE
from alexandriabase.domain import PaginatedResult, Document, Tree, EventType,\
    EventTypeIdentifier, Event

# Patching PyPDF2
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
from PyPDF2 import utils
def read_inline_image_patch(self, stream):
    '''
    Overrides the _readInlineImage method in the
    ContentStream class to speed up data reading
    '''
    # begin reading just after the "BI" - begin image
    # first read the dictionary of settings.
    settings = DictionaryObject()
    while True:
        tok = readNonWhitespace(stream)
        stream.seek(-1, 1)
        if tok == b_("I"):
            # "ID" - begin of image data
            break
        key = readObject(stream, self.pdf)
        tok = readNonWhitespace(stream)
        stream.seek(-1, 1)
        value = readObject(stream, self.pdf)
        settings[key] = value
    # left at beginning of ID
    tmp = stream.read(3)
    assert tmp[:2] == b_("ID")
    # pylint: disable=protected-access
    data = self._readImagaDataFast(stream)
    return {"settings": settings, "data": data}

def read_imaga_data_fast(self, stream):
    '''
    Buffered reading of image data. The unpatched version
    did read byte by byte which is incredible slow on large
    images.
    '''
    # pylint: disable=unused-argument
    # We keep more than buffersize bytes in the buffer because the
    # end of image sequence might overlap. So we search some data twice,
    # but this is still far more effective than the old algorithm
    buffersize = 1024 * 1024 # Extracting in megabyte chunks
    buffertail = 256
    regex = re.compile(b_("(.*?)(EI\\s+)Q\\s+"), re.DOTALL)
    data = b_("")
       
    buffer = stream.read(buffersize+buffertail)
    
    end_of_image = False   
    while not end_of_image:
        
        match = regex.match(buffer)
        if match:
            data += buffer[:len(match.group(1))]
            stream.seek(-1 * (len(buffer) - len(match.group(1)) - len(match.group(2))), 1)
            end_of_image = True
        else:
            if len(buffer) < buffersize + buffertail: # We already have exhausted the stream
                raise utils.PdfReadError("Didn't find end of image marker!")
            data += buffer[:buffersize]
            buffer = buffer[buffersize:] + stream.read(buffersize)

    return data
#pylint: disable=protected-access
ContentStream._readInlineImage = read_inline_image_patch
ContentStream._readImageDataFast = read_imaga_data_fast 

# End of patchinv PyPDF2

class UnsupportedFileFormat(Exception):
    '''
    Raised when the given file format is not
    supported.
    
    Argument:
        format The offending format
    '''
    def __init__(self, file_format):
        # pylint: disable=super-init-not-called
        self.file_format = file_format
        
class UnsupportedFileResolution(Exception):
    '''
    Raised, when the fileformat is supported,
    but not with this resolution.
    '''
    def __init__(self, file_format, resolution):
        # pylint: disable=super-init-not-called
        self.file_format = file_format
        self.x_resolution = resolution
        self.y_resolution = resolution
        
class DifferentXAndYResolutions(UnsupportedFileResolution):
    '''
    Raised, when the x resolutions does not match the
    y resolution.
    '''
    
    def __init__(self, x_resolution, y_resolution):
        # pylint: disable=super-init-not-called
        self.file_format = None
        self.x_resolution = x_resolution
        self.y_resolution = y_resolution

def get_graphic_file_resolution(file):
    '''
    Gets the resolution from the info property of a PIL image
    '''
    image = Image.open(file)
    file_info = image.info
    if not 'dpi' in file_info:
        return None
    x_res = file_info['dpi'][0]
    y_res = file_info['dpi'][1]
    # In newer versions of Pillow the resolution
    # is an object of type IFDRational that is
    # not simply comparable - equality checks for identity
    if "%s" % x_res != "%s" % y_res:
        raise DifferentXAndYResolutions(x_res, y_res)
    return x_res

def get_gif_file_resolution(file):
    # pylint: disable=unused-argument
    '''
    Gifs always have a resolution of 72 dpi. In the early days of
    the first alexandria implementation we scanned with 300 dpi
    and converted it straight to a gif file. So in fact our gifs
    have 300 dpi 
    '''
    return 300

class BaseRecordService():
    '''
    classdocs
    '''
    def __init__(self, dao, filter_expression_builder):
        '''
        The constructor expects the dao for the record type
        as parameter and a dao specific filter expression builder.
        '''
        self.dao = dao
        self.filter_expression_builder = filter_expression_builder
    
    def get_by_id(self, object_id):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_by_id(object_id)
        
    def get_first(self, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_first(filter_expression)
    
    def get_next(self, entity, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_next(entity, filter_expression)
    
    def get_previous(self, entity, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_previous(entity, filter_expression)
    
    def get_last(self, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_last(filter_expression)
    
    def get_nearest(self, entity_id, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_nearest(entity_id, filter_expression)
    
    def create_filter_expression(self, filter_object):
        '''
        Uses a dao specific filter object to build a filter expression
        '''
        return self.filter_expression_builder.create_filter_expression(filter_object)
    
    def save(self, entity):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.save(entity)

    def delete(self, entity):
        '''
        Just reaches through to the dao.
        '''
        self.dao.delete(entity.id)

    def find(self, condition, page, page_size):
        '''
        Finds documents and wraps them with a PaginatedResult
        '''
        
        result = PaginatedResult()
        result.page = page
        result.page_size = page_size
        number_of_entities = self.dao.get_count(condition)
        result.number_of_pages = ceil((number_of_entities * 1.0) / page_size)
        result.entities = self.dao.find(condition, page, page_size)
        return result

class CreatorService(object):
    '''
    Service to manage the creators in the database.
    '''

    @inject
    def __init__(self, creator_dao: baseinjectorkeys.CREATOR_DAO_KEY):
        '''
        Uses the creator dao for database access
        '''
        self.creator_dao = creator_dao
        
    def find_all_active_creators(self):
        '''
        Returns all creators that have the visible flag set.
        '''
        return self.creator_dao.find_all_visible()

def get_version(connection):
    '''
    TODO: Use registry dao
    Reads the current database version from the registry table
    '''
    query = select([REGISTRY_TABLE])\
        .where(REGISTRY_TABLE.c.schluessel == 'version')  # @UndefinedVariable
    result = connection.execute(query)
    row = result.fetchone()
    return row[REGISTRY_TABLE.c.wert]  # @UndefinedVariable


class BaseUpdate():
    '''
    Baseclass for update classes that provider the set_version method
    '''
    
    def __init__(self, connection, dialect):
        self.connection = connection
        self.dialect = dialect
        
    def set_version(self, version):
        '''
        Updates the registry table to set the current version
        '''
        
        query = update(REGISTRY_TABLE)\
            .values(wert=version)\
            .where(REGISTRY_TABLE.c.schluessel == 'version')  # @UndefinedVariable
        self.connection.execute(query)

class UpdateFrom0_3(BaseUpdate):
    # pylint: disable=invalid-name
    '''
    Updates from version 0.3 to 0.4 (removes annoying not null constraints)
    '''
    
    dialect_specifics = {'sqlite': '',
                         'postgresql': 'alter table dokument alter seite drop not null, ' +
                                       'alter dateityp drop not null'}
    
    def run(self):
        '''
        Runs the upgrade
        '''
        self.connection.execute(text(self.dialect_specifics[self.dialect]))
        self.set_version('0.4')

class DatabaseUpgradeService():
    '''
    Handles updating the database
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        '''
        Constructor
        '''
        self.db_engine = db_engine
        
    def is_update_necessary(self):
        '''
        Informs about necessity for an upgrade
        '''
        connection = self.db_engine.connect()
        db_version = get_version(connection)
        connection.close()
        return db_version != CURRENT_VERSION
    
    def run_update(self):
        '''
        Runs all unapplied upgrades in a transaction. Rolls back,
        if something goes wrong and throws received exception again.
        '''
        connection = self.db_engine.connect()
        transaction = connection.begin()
        try:
            db_version = get_version(connection)
            while db_version != CURRENT_VERSION:
                class_name = 'UpdateFrom' + db_version.replace('.', '_')
                updater_class = getattr(sys.modules[self.__module__], class_name)
                updater = updater_class(connection, self.db_engine.name)
                updater.run()
                db_version = get_version(connection)
        except Exception as exception:
            transaction.rollback()
            raise exception
        transaction.commit()
        connection.close()

LINES_ARE_PARAGRAPHS = 'Lines are paragraphs'
EMPTY_LINES_ARE_SEPARATORS = 'Empty lines are separators'
SHORT_LINES_ARE_PARBREAKS = 'Short lines are paragraph breaks'

class TextObject(object):
    '''
    Abstract representation of a text file to extract paragraphs
    for pdf generation.
    '''
    
    _re_empty_line = re.compile(r"^\s+$")

    def __init__(self, file_name):
        file = self._open_file(file_name)
        self.lines = []
        self.number_of_lines = 0
        self.empty_lines = 0
        self.max_length = 0
        for line in file:
            self._add_line(line)
        file.close()
        
    def _open_file(self, file_name):
        '''
        Determines if we have an old latin1 file or a new unicode file
        '''
        # pylint: disable=no-self-use
        try:
            file = open(file_name, 'r')
            file.read()
        except UnicodeDecodeError:
            file.close()
            return codecs.open(file_name, 'r', 'latin1')
        file.close()
        return open(file_name, 'r')

    def _add_line(self, line):
        self.lines.append(line)
        self.number_of_lines += 1
        if self._is_line_empty(line):
            self.empty_lines += 1
            return
        if len(line) > self.max_length:
            self.max_length = len(line)
        
    def _is_line_empty(self, line):
        return self._re_empty_line.match(line)
        
    def _get_short_line_length(self):
        return self.max_length * 0.8
    
    def get_paragraphs(self):
        '''
        Tries to split the text file into paragraphs according
        to some file characteristics. May not be one hundret percent
        accurate.
        '''
        if self.max_length > 120:
            return self._use_lines_as_paragraphs()
        if self.empty_lines > 2:
            return self._use_empty_lines_as_separators()
        return self._use_short_lines_as_separators()

    def _use_lines_as_paragraphs(self):
        paragraphs = []
        counter = 0
        for line in self.lines:
            if not self._is_line_empty(line):
                paragraphs.append(line)
                counter += 1
        return paragraphs
    
    def _use_empty_lines_as_separators(self):        
        paragraphs = []
        lines = []
        counter = 0
        for line in self.lines:
            if self._is_line_empty(line):
                paragraphs.append("".join(lines))
                counter += 1
                lines = []
            else:
                lines.append(line)
        paragraphs.append("".join(lines))
        return paragraphs

    def _use_short_lines_as_separators(self):
        short = self._get_short_line_length()
        paragraphs = []
        lines = []
        counter = 0
        for line in self.lines:
            lines.append(line)
            if len(line) < short:
                paragraphs.append("".join(lines))
                lines = []
                counter += 1
        paragraphs.append("".join(lines))
        return paragraphs
        
class TextPdfHandler(object):
    '''
    Handler class for text files. Converts text into paragraph
    flowables.
    '''

    _re_empty_line = re.compile(r"^\s+$")
    
    @inject
    def __init__(self, document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY):
        '''
        Constructor
        '''
        self.first_paragraph = ParagraphStyle('First',
                                              fontName='Helvetica-Bold',
                                              fontSize=18,
                                              leading=20,
                                              spaceBefore=10,
                                              spaceAfter=10,
                                              leftIndent=2 * cm,
                                              rightIndent=2 * cm)
        self.second_paragraph = ParagraphStyle('Second',
                                               fontName='Helvetica-Bold',
                                               fontSize=16,
                                               leading=18,
                                               spaceBefore=10,
                                               spaceAfter=10,
                                               leftIndent=2 * cm,
                                               rightIndent=2 * cm)
        self.normal_style = ParagraphStyle('Normal',
                                           fontName='Helvetica',
                                           fontSize=12,
                                           leading=16,
                                           spaceBefore=10,
                                           spaceAfter=10,
                                           leftIndent=2 * cm,
                                           rightIndent=2 * cm)
        self.document_file_manager = document_file_manager
        self.styles = [self.first_paragraph, self.second_paragraph]

    def add_document_file_to_story(self, story, file_info, margins):
        '''
        The handler method. Adds the flowables to the story. The margins
        parameter is not used in this handler because the paragraphs get
        automatically alligned to the margins of the containing frame.
        '''
        # pylint: disable=unused-argument
        file_name = self.document_file_manager.get_file_path(file_info)
        text_object = TextObject(file_name)
        paragraphs = text_object.get_paragraphs()
        for par in paragraphs[0:1]:
            story.append(Paragraph(par, self.first_paragraph))
        for par in paragraphs[1:2]:
            story.append(Paragraph(par, self.second_paragraph))
        for par in paragraphs[2:]:
            story.append(Paragraph(par, self.normal_style))
        return story

class GraphicsPdfHandler(object):
    '''
    Handler for graphic formats.
    '''
    
    @inject
    def __init__(self, document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY):
        '''
        Constructor
        '''
        self.document_file_manager = document_file_manager
        self.frame_width = 583
        self.frame_height = 829

    def add_document_file_to_story(self, story, file_info, margins):
        '''
        The handler method. Scales the images either to fit on a page (if
        they are larger) or to the proper size according to the given
        file resolution.
        '''
        file = self.document_file_manager.get_file_path(file_info)
        available_width = self.frame_width - margins * 2 * cm
        available_height = self.frame_height - margins * 2 * cm
        
        image = PdfImage(file)
        if image.imageWidth > available_width or image.imageHeight > available_height:
            # scale down to 
            factor = available_width / image.imageWidth
            height_factor = available_height / image.imageHeight
            if height_factor < factor:
                factor = height_factor
            story.append(PdfImage(file, image.imageWidth*factor, image.imageHeight*factor))
        else:
            # calculate size
            resolution = file_info.resolution
            if not resolution:
                resolution = 300.0
            width_in_inch = image.imageWidth / resolution
            height_in_inch = image.imageHeight / resolution
            story.append(PdfImage(file, width_in_inch * inch, height_in_inch * inch))
        return story

class DocumentPdfGenerationService(object):
    '''
    Service to create a pdf file from the systematic database
    entries
    '''
    # pylint: disable=no-self-use

    @inject
    def __init__(self,
                 document_file_info_dao: baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
                 document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                 pdf_handlers: baseinjectorkeys.PDF_HANDLERS_KEY):
        '''
        Constructor
        '''
        self.document_file_info_dao = document_file_info_dao
        self.document_file_manager = document_file_manager
        self.pdf_handlers = pdf_handlers
    
    def generate_document_pdf(self, document):
        '''
        The public method to create a pdf file for a document
        
        Returns the pdf as byte buffer
        '''
        
        file_infos = self.document_file_info_dao.get_file_infos_for_document(document.id)
        return self._run_generation(file_infos)

    def generate_file_pdf(self, document_file_info):
        '''
        The public method to create a pdf file for just one document file
        
        Returns the pdf as byte buffer
        '''
        
        return self._run_generation([document_file_info])

    def _run_generation(self, file_infos):
        
        if self._contains_text_content(file_infos):
            margins = 1.5
        else:
            margins = 0.0
            
        pdf_list = []
        story = []
        for file_info in file_infos:
            
            if file_info.filetype == 'pdf':
                if story:
                    pdf_list.append(self._build_pdf(story, margins))
                    story = []
                path = self.document_file_manager.get_file_path(file_info)
                file = open(path, "rb")
                pdf_list.append(file.read())
                file.close()
                continue
            
            if file_info.filetype in self.pdf_handlers.keys():
                story = self.pdf_handlers[file_info.filetype].\
                    add_document_file_to_story(story, file_info, margins)
            else:
                story = self._add_no_handler_warning(story, file_info)
        
        if story:
            pdf_list.append(self._build_pdf(story, margins))
        
        return self._join_pdfs(pdf_list)
        
    def _build_pdf(self, story, margins):
        
        file = BytesIO()
        doc = SimpleDocTemplate(file,
                                pagesize=A4,
                                leftMargin=margins * cm,
                                rightMargin=margins * cm,
                                topMargin=margins * cm,
                                bottomMargin=margins * cm)
        doc.build(story)
        return file.getvalue()

    def _join_pdfs(self, pdf_list):
        
        if len(pdf_list) == 1:
            return pdf_list[0]
        pdf_merger = PdfFileMerger()
        for pdf in pdf_list:
            pdf_file = BytesIO(pdf)
            pdf_merger.append(pdf_file)
        output = BytesIO()
        pdf_merger.write(output)
        pdf_merger.close()
        return output.getvalue()
        
    def _contains_text_content(self, file_infos):
    
        for file_info in file_infos:
            if file_info.filetype == 'txt':
                return True
        return False
       
    def _add_no_handler_warning(self, story, file_info):
        style = ParagraphStyle('Normal', None)
        style.fontSize = 18
        style.leading = 20
        style.spaceBefore = 12
        style.spaceAfter = 12
        paragraph = Paragraph("It is not possible to represent document file %s as pdf." 
                              % file_info, style)
        story.append(paragraph)
        return story

THUMBNAIL = 'thumbnail'
DISPLAY_IMAGE = 'display_image'
DOCUMENT_PDF = 'document_pdf'

class DocumentFileNotFound(Exception):
    '''
    Exception class for not found files
    '''
    # pylint: disable=super-init-not-called
    def __init__(self, document_file_info):
        self.document_file_info = document_file_info

class NoImageGeneratorError(Exception):
    '''
    Exception class for not found files
    '''
    # pylint: disable=super-init-not-called
    def __init__(self, filetype):
        self.filetype = filetype

class ImageExtractionFailure(Exception):
    '''
    Exception class for failed image extraction
    '''
    # pylint: disable=super-init-not-called
    def __init__(self, file_path, return_value):
        self.file_path = file_path
        self.return_value = return_value
        
class FileProvider():
    '''
    Provides the content of different derived files for documents. The
    files will generated, if they do not already exist. This should
    be relatively fail safe, provided that the original files exist.
    '''
    # pylint: disable=no-self-use
    @inject
    def __init__(self,
                 document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY, 
                 document_file_info_dao: baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
                 document_pdf_generator: baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY,
                 document_file_image_generator: baseinjectorkeys.DOCUMENT_FILE_IMAGE_GENERATOR_KEY):
        
        self.document_file_manager = document_file_manager
        self.document_file_info_dao = document_file_info_dao
        self.document_pdf_generator = document_pdf_generator
        self.document_file_image_generator = document_file_image_generator
        
    def get_pdf(self, document):
        '''
        Returns (and creates if necessary) the pdf file for a document.
        TODO: Bug if there is no file attached yet to the document
        '''
        try:
            document_file_info = self.document_file_info_dao.get_by_id(document.id)
        except NoSuchEntityException:
            # Quick fix, reconsider 
            raise DocumentFileNotFound(None)
        
        try:
            return self.document_file_manager.get_generated_file(document_file_info, DOCUMENT_PDF)
        except FileNotFoundError:
            pass
        # if we get here, we have to generate the pdf
        pdf = self.document_pdf_generator.generate_document_pdf(document)
        self.document_file_manager.add_generated_file(pdf, document_file_info, DOCUMENT_PDF)
        return pdf
    
    def get_thumbnail(self, document_file_info):
        '''
        Returns (and creates if necessary) the thumbnail file for a document file 
        '''
        try:
            return self.document_file_manager.get_generated_file(document_file_info, THUMBNAIL)
        except FileNotFoundError:
            pass
        try:
            pil_img = self.document_file_image_generator.generate_image(document_file_info)
        except NoImageGeneratorError:
            pil_img = self._create_no_thumbnail_image(document_file_info)
        
        pil_img.thumbnail((200, 258))
        if pil_img.mode == "CMYK":
            pil_img = pil_img.convert("RGB")
        file_buffer = BytesIO()
        try:
            pil_img.save(file_buffer, 'png')
        except IOError as error:
            print("Error saving file %s" % document_file_info)
            raise error
        thumbnail = file_buffer.getvalue()
        self.document_file_manager.add_generated_file(thumbnail, document_file_info, THUMBNAIL)
        return thumbnail
        
    def get_display_image(self, document_file_info):
        '''
        Returns (and creates if necessary) a display image file for a document file 
        '''
        try:
            return self.document_file_manager.get_generated_file(document_file_info, DISPLAY_IMAGE)
        except FileNotFoundError:
            pass
        try:
            pil_img = self.document_file_image_generator.generate_image(document_file_info)
        except NoImageGeneratorError:
            pil_img = self._create_no_display_image(document_file_info)
        
        resolution = document_file_info.resolution
        if resolution is None:
            resolution = 72
        scaling_factor = 108.0 / resolution
        scaled_width = int(pil_img.size[0] * scaling_factor)
        scaled_height = int(pil_img.size[1] * scaling_factor)
        pil_img = pil_img.resize((scaled_width, scaled_height))
        if pil_img.mode == "CMYK":
            pil_img = pil_img.convert("RGB")
        file_buffer = BytesIO()
        pil_img.save(file_buffer, 'png')
        display_image = file_buffer.getvalue()
        self.document_file_manager.add_generated_file(display_image,
                                                      document_file_info,
                                                      DISPLAY_IMAGE)
        return display_image

    def _create_no_thumbnail_image(self, document_file_info):
        img = Image.new('P', (400, 440), color=255)
        font = ImageFont.truetype(os.path.join(fontdir, "Arial_Bold.ttf"), 48)
        draw = ImageDraw.Draw(img)
        draw.text((10, 60), "Keine Vorschau", font=font, fill=0)
        draw.text((10, 120), "für Datei", font=font, fill=0)
        draw.text((10, 180), document_file_info.get_file_name(), font=font, fill=0)
        return img

    def _create_no_display_image(self, document_file_info):
        img = Image.new('P', (400, 440), color=255)
        font = ImageFont.truetype(os.path.join(fontdir, "Arial_Bold.ttf"), 48)
        draw = ImageDraw.Draw(img)
        draw.text((10, 60), "Keine Graphik", font=font, fill=0)
        draw.text((10, 120), "für Datei", font=font, fill=0)
        draw.text((10, 180), document_file_info.get_file_name(), font=font, fill=0)
        return img
        
class DocumentFileImageGenerator:
    '''
    Main class for image generation. There are handlers for different
    file types to create an image (there should be more). Throws a
    NoImageGeneratorError if it is no possible to create an image from
    a file.
    '''
    
    @inject
    def __init__(self, image_generators: baseinjectorkeys.IMAGE_GENERATORS_KEY):
        
        self.image_generators = image_generators
        
    def generate_image(self, document_file_info):
        '''
        Invokes the appropriate handler for the file type to generate an image
        '''
        try:
            return self.image_generators[document_file_info.filetype].\
                generate_image(document_file_info)
        except KeyError:
            raise NoImageGeneratorError(document_file_info.filetype)
        
class GraphicsImageGenerator:
    '''
    A simple image "generator" for graphics file: Just opens the graphic
    file as PIL image
    '''
 
    @inject
    def __init__(self, document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY):   
        self.document_file_manager = document_file_manager
        
    def generate_image(self, document_file_info):
        '''
        Opens the file as PIL image
        '''
        return Image.open(self.document_file_manager.get_file_path(document_file_info))
        
class PdfImageGenerator:
    '''
    Create an image from a pdf file
    '''
    
    @inject
    def __init__(self, document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                 pdf_image_extractor: baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY):
        self.document_file_manager = document_file_manager
        self.pdf_image_extractor = pdf_image_extractor
        
    def generate_image(self, document_file_info):
        '''
        Uses the pdf image extractor to get an image from the pdf file
        '''
        file_path = self.document_file_manager.get_file_path(document_file_info)
        return self.pdf_image_extractor.extract_image(file_path)

class TextImageGenerator:
    '''
    To convert a text file into an image, this handler first
    creates a pdf file from the text file and then extracts
    an image from the pdf file.
    '''
    
    @inject
    def __init__(self,
                 pdf_image_extractor: baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY,
                 pdf_generator: baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY):
        self.pdf_image_extractor = pdf_image_extractor
        self.pdf_generator = pdf_generator
        
    def generate_image(self, document_file_info):
        '''
        Writes a temporary pdf file and then uses the pdf image extractor
        to create an image from the pdf
        '''
        pdf_from_text = self.pdf_generator.generate_file_pdf(document_file_info)
        tmp_file = tempfile.NamedTemporaryFile(mode="wb", suffix='.pdf', delete=False)
        tmp_file.write(pdf_from_text)
        tmp_file.close()
        image = self.pdf_image_extractor.extract_image(tmp_file.name)
        os.unlink(tmp_file.name)
        return image
    
class MovieImageGenerator:
    '''
    Generates an image from a movie file 4 seconds into the movie
    '''
    
    @inject
    def __init__(self, document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY):   
        self.document_file_manager = document_file_manager
        
    def generate_image(self, document_file_info):
        '''
        Uses ffmpeg to write a frame of the given video as jpg file that then will
        be read into a PIL image and the file removed. 
        '''
        
        
        input_file_name = self.document_file_manager.get_file_path(document_file_info)
        tmp_file = tempfile.NamedTemporaryFile(mode="wb", suffix='.jpg', delete=False)
        tmp_file.close()
        output_file_name = tmp_file.name
        stdio = open(os.devnull, 'wb')
        call(["ffmpeg",
              "-itsoffset", "-4",
              "-i", input_file_name,
              "-vcodec", "mjpeg",
              "-vframes", "1",
              "-an", 
              "-f", "rawvideo",
              "-y",
              output_file_name
             ],
             stdout=stdio,
             stderr=stdio)
        image = Image.open(output_file_name)
        os.unlink(output_file_name)
        return image
    
class PdfImageExtractor(object):
    '''
    Creates PIL images from pdf files. First tries to extract
    image data directly from the pdf file, then, when this fails,
    uses ghostscript to render the first page of the pdf.
    
    The code is mostly based on information found at
    http://stackoverflow.com/questions/2693820/extract-images-from-pdf-without-resampling-in-python
    
    There is a lot of exception caching and handling in this class
    because there are pdfs out in the wild you would not believe could
    exist. This class consistently throws an ImageExtractionFailure
    when something goes fatally wrong. But be aware it might return a
    blank image without notifying you of any failure anything. Or the
    image might fail when working on it.
    '''
    # pylint: disable=no-self-use
    
    def __init__(self):
        self.data_extractors = {'/FlateDecode': self._decode_data,
                                '/DCTDecode': self._extract_jpg_data,
                                '/JPXDecode': self._extract_jpg_data,
                                '/CCITTFaxDecode': self._extract_ccitt_fax}
        self.logger = logging.getLogger()

    def extract_image(self, path):
        '''
        The public method to extract an image from a pdf file
        
        This is much too sophisticated since in 99.9% of the cases
        we need ghostscript to extract the image file, either because
        there is text on the page or there are multiple images. Or
        there are errors only ghostscript is able to handle.
        
        But since the code is written, we use it.
        '''
        # pylint: disable=broad-except
        # pylint: disable=too-many-return-statements
        try:
            pdf_reader = PdfFileReader(open(path, "rb"))
        except Exception as error:
            self.logger.debug("Trying ghostscript due to pyPDF2 read failure (%s).", error)
            return self._extract_using_ghostscript(path)
            
        if pdf_reader.isEncrypted:
            self.logger.debug("Trying ghostscript on encrypted pdf.")
            return self._extract_using_ghostscript(path)

        try:
            page0 = pdf_reader.getPage(0)
        except Exception as error:
            self.logger.debug("Trying ghostscript due to page read failure (%s).", error)
            return self._extract_using_ghostscript(path)
            
        try:
            page_text = page0.extractText()
        except Exception as error:
            self.logger.debug("Trying ghostscript due " +
                              "to error extracting text from pdf (%s).", error)
            return self._extract_using_ghostscript(path)

        if page_text != '':
            return self._extract_using_ghostscript(path)
        
        image_objects = self._find_image_objects(page0)
        if len(image_objects) != 1:
            # If we have zero images, we need to use ghostscript
            # If there are several images, it is too complicated to join them
            self.logger.debug("Using ghostscript (number of extractable " +
                              "images is %d).", len(image_objects))
            return self._extract_using_ghostscript(path)
        
        image_object = image_objects[0]
        try:
            filter_type = image_object["/Filter"]
            if not isinstance(filter_type, list):
                filter_type = (filter_type,)
            for handler_key in self.data_extractors:
                if handler_key in filter_type:
                    self.logger.debug("Extracting for filter type %s", filter_type)
                    return self.data_extractors[handler_key](image_object)
        except Exception as error:
            if self.logger.getEffectiveLevel() == logging.DEBUG:
                self.logger.exception("Exception running extractor (%s).", error)

        # if we did not succeed for whatever reason, we fall back
        # to interpreting the pdf file using ghostscript
        self.logger.debug("Using ghostscript due to exception.")
        return self._extract_using_ghostscript(path)
                
    def _extract_using_ghostscript(self, pdf_path):
        '''
        We can't successfully extract an wrapped image, so we have to render the pdf ourselves.
        '''
        tmp_file = tempfile.NamedTemporaryFile("wb")
        path = tmp_file.name
        tmp_file.close()
        
        stdio = open(os.devnull, 'wb')
        return_value = call(["gs",
                             "-sDEVICE=png16m",
                             "-dNOPAUSE", "-dFirstPage=1",
                             "-dLastPage=1",
                             "-sOutputFile=%s" % path,
                             "-r300",
                             "-q",
                             pdf_path,
                             "-c",
                             "quit"],
                            stdout=stdio,
                            stderr=stdio)
        
        if return_value != 0:
            # pylint: disable=bare-except
            try:
                os.unlink(path)
            except:
                pass
            raise ImageExtractionFailure(path, return_value)
        
        img = Image.open(path)
        os.unlink(path)
        return img
        

    def _generate_tiff_header_for_ccitt_fax(self, width, height, data_size, compression):
        '''
        Auxiliary method to create a tiff header from meta data information
        '''
        tiff_header_struct = '<' + '2s' + 'h' + 'l' + 'h' + 'hhll' * 8 + 'l'
        return struct.pack(tiff_header_struct,
                           # Byte order indication: Little indian
                           b'II',
                           # Version number (always 42)
                           42,
                           # Offset to first IFD
                           8,
                           # Number of tags in IFD
                           8,
                           # ImageWidth, LONG, 1, width
                           256, 4, 1, width,
                           # ImageLength, LONG, 1, lenght
                           257, 4, 1, height,
                           # BitsPerSample, SHORT, 1, 1
                           258, 3, 1, 1,
                           # Compression, SHORT, 1, 4 = CCITT Group 4 fax encoding
                           259, 3, 1, compression, 
                           # Threshholding, SHORT, 1, 0 = WhiteIsZero          
                           262, 3, 1, 0,  
                           # StripOffsets, LONG, 1, len of header
                           273, 4, 1, struct.calcsize(tiff_header_struct),
                           # RowsPerStrip, LONG, 1, lenght  
                           278, 4, 1, height,
                           # StripByteCounts, LONG, 1, size of image
                           279, 4, 1, data_size, 
                           # last IFD         
                           0
                          )

    def _extract_ccitt_fax(self, image_object):
        '''
        Tiff data may be stored as raw fax data without tiff header,
        so it is necessary to create a tiff header for the data to
        let PIL interpret the data correctly
        '''
        # pylint: disable=protected-access        
        width = image_object['/Width']
        height = image_object['/Height']
        data = image_object._data  # sorry, getData() does not work for CCITTFaxDecode
        #length = image_object['/Length']
        #length = 4711
        compression_map = {-1: 4, 0: 2, 1: 3}
        compression = compression_map[image_object['/DecodeParms']['/K']]
        tiff_header = self._generate_tiff_header_for_ccitt_fax(width,
                                                               height,
                                                               len(data),
                                                               compression)
        return Image.open(BytesIO(tiff_header + data))
        
    def _extract_jpg_data(self, image_object):
        '''
        There is (theoretically) no decoding to be done, so we
        use the raw stream data (_data) without the decoding
        hidden behind getData().
        And then we let PIL determine from the header data what to do.
        This does not work reliably, so we have to test the image
        data and provoke an exception if it did not work
        
        Well, it should work correctly. One of the sample files
        generated with tiff2pdf does not work correctly, but this
        seems to be the fault of tiff2pdf. Anyway, there might
        be more corrupt pdfs in the wild, so we retain the test code.
        '''
        # pylint: disable=protected-access        
        data = image_object._data
        image = Image.open(BytesIO(data))
        # Simple check that the image data could be interpreted and can be written
        # as png file
        file = BytesIO()
        image.save(file, 'png')
        file.close()
        return image
    
    def _decode_data(self, image_object):
        '''
        We have just raw data, so we let pyPDF2 do the
        decoding and then extract size and
        colorspace from the meta data to give PIL the
        information to correctly decode the data
        '''
        size = (image_object['/Width'], image_object['/Height'])
        data = image_object.getData()
        if image_object['/ColorSpace'] == '/DeviceRGB':
            self.logger.debug("Extracting RGB color image")
            mode = "RGB"
        else:
            self.logger.debug("Extracting black and white image")
            mode = "P"
        return Image.frombytes(mode, size, data)

    def _find_image_objects(self, page):
        '''
        Loops over the objects and tries to find an image
        '''
        image_objects = []

        try:
            if not '/Resources' in page:
                self.logger.debug("PdfReadError: Missing /Resources in page.")
                return image_objects
            if not '/XObject' in page['/Resources']:
                self.logger.debug("No /XObject in /Resources.")
                return image_objects
        except PdfReadError as error:
            self.logger.debug("PdfReadError: %s", error)
            return image_objects

        x_object = page['/Resources']['/XObject'].getObject()

        for obj in x_object:
            if '/Subtype' in x_object[obj] and x_object[obj]['/Subtype'] == '/Image':
                image_objects.append(x_object[obj])
        return image_objects

class DocumentFileManager(object):
    '''
    A simple class to manage document files. It provider
    all the methods needed to create, delete or find files
    referenced by a document file info.
    It also supports handling of derived files (pdfs, thumbnails etc.)
    '''
    # pylint: disable=no-self-use
    @inject
    def __init__(self, config_service: baseinjectorkeys.CONFIG_KEY,
                 document_file_info_dao: baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY):
        '''
        Constructor reads the configuration from the config_service
        '''
        self.base_dir = config_service.document_dir
        self.archives = config_service.archive_dirs
        self.document_file_info_dao = document_file_info_dao
        self.path_handler = {THUMBNAIL: self._get_thumb_path,
                             DISPLAY_IMAGE: self._get_display_path,
                             DOCUMENT_PDF: self._get_pdf_path}
        self.logger = logging.getLogger(
            "alexandriabase.services.documentfilemanager.DocumentFileManager")

    def delete_file(self, document_file_info):
        '''
        Does not physically delete files but appends their file name
        with .deleted
        '''
        file_path = self.get_file_path(document_file_info)
        shutil.move(file_path, "%s.deleted" % file_path)

    def add_file(self, file_path, document_file_info):
        '''
        Adds a file to the DOCUMENTBASEDIR, renaming it according
        to the information in the document file info and deletes
        the original file
        '''
        directory_path = self._create_type_dir_path(document_file_info)
        if not os.path.exists(directory_path):
            os.makedirs(directory_path)
        shutil.copy(file_path, os.path.join(directory_path, document_file_info.get_file_name()))
        os.remove(file_path)

    def get_file_path(self, document_file_info):
        '''
        Searches in the BASEDIR and then in the ARCHIVES for the
        referenced file. Raises a DocumentFileNotFound exception
        if not found.
        '''
        self.logger.debug("Searching for file %s", document_file_info)
        basedir_path = self._create_basedir_path(document_file_info)
        
        self.logger.debug("Searching in %s", basedir_path)
        if os.path.isfile(basedir_path):
            return basedir_path

        expanded_short_path = self._create_archive_sub_path(document_file_info)

        for archive in self.archives:
            archive_path = os.path.join(archive, expanded_short_path)
            self.logger.debug("Searching in %s", archive_path)
            if os.path.isfile(archive_path):
                return archive_path
        raise DocumentFileNotFound(document_file_info)

    def get_generated_file_path(self, document_file_info, generation_type):
        '''
        Returns the path of the generated file belonging to the master
        file given in the document_file_info of the given generation_type
        '''
        
        return self.path_handler[generation_type](document_file_info)
        
    def _get_thumb_path(self, document_file_info):
        '''
        Returns the location of the thumbnail path
        '''
        return self._get_path(document_file_info, "thumb", "png")
    
    def _get_display_path(self, document_file_info):
        '''
        Returns the location of the display image path
        '''
        return self._get_path(document_file_info, "display", "png")

    def _get_pdf_path(self, document_file_info):
        '''
        Returns the location of the pdf file path
        '''
        if document_file_info.id == document_file_info.document_id:
            file_info = document_file_info
        else:
            file_info = self.document_file_info_dao.get_by_id(document_file_info.document_id)
        return self._get_path(file_info, "pdf", "pdf")

    def _get_path(self, document_file_info, subdir, extension):
        '''
        Use regular expressions to manipulate the master file
        path for derived files
        '''
        file_path = self.get_file_path(document_file_info)
        ftype = document_file_info.filetype
        subdir_path = re.sub(r"/%s/(?=\d{8}\.%s)" % (ftype, ftype),
                             r"/%s/%s/" % (ftype, subdir),
                             file_path)
        return re.sub(r"\.%s$" % ftype, ".%s" % extension, subdir_path)
    
    def get_generated_file(self, document_file_info, generation_type):
        '''
        Returns the file as bytes if it exists. May throw a FileNotFound exception.
        '''
        
        path = self.get_generated_file_path(document_file_info, generation_type)
        file = open(path, mode="rb")
        content = file.read()
        file.close()
        return content
        
    def add_generated_file(self, byte_buffer, document_file_info, generation_type):
        '''
        Add the generated file at its appropriate place.
        '''
        
        path = self.get_generated_file_path(document_file_info, generation_type)
        path_dir = os.path.dirname(path) 
        try:
            os.makedirs(path_dir)
        except FileExistsError:
            pass
        file = open(path, mode="wb")
        file.write(byte_buffer)
        file.close()
    
    def delete_generated_file(self, document_file_info, generation_type):
        '''
        Removes the generated file if it exists. Otherwise does nothing.
        Also nothing happens when the original document just has is a single
        pdf file and there is a request to delete the generated pdf file for
        the document.
        '''
        try:
            os.unlink(self.get_generated_file_path(document_file_info, generation_type))
        except FileNotFoundError:
            pass
    
    def _create_basedir_path(self, document_file_info):
        '''
        Creates a path for the file in the base dir
        '''
        return os.path.join(self.base_dir,
                            self._create_path_with_typedir(document_file_info))

    def _create_type_dir_path(self, document_file_info):
        return os.path.join(self.base_dir,
                            document_file_info.filetype)

    def _create_path_with_typedir(self, document_file_info):
        '''
        Helper function for path construction
        '''
        return os.path.join(
            document_file_info.filetype,
            document_file_info.get_file_name())

    def _create_archive_sub_path(self, document_file_info):
        '''
        When documents are archived, then they are stored in 1000 blocks.
        The first 1000 files (0-999) go into the directory 1000, then next
        1000 files (1000-1999) into the directory 2000 and so on.
        '''
        dirnumber = ((document_file_info.id + 1000) // 1000) * 1000
        return os.path.join("%d" % dirnumber,
                            self._create_path_with_typedir(document_file_info))

class DocumentService(BaseRecordService):
    '''
    Service to bundle the complicated document file management
    with the database information
    '''

    @inject
    def __init__(self,
                 dokument_dao: baseinjectorkeys.DOCUMENT_DAO_KEY,
                 document_file_info_dao: baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
                 document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                 document_type_dao: baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY,
                 document_file_provider: baseinjectorkeys.DOCUMENT_FILE_PROVIDER,
                 ereignis_dao: baseinjectorkeys.EVENT_DAO_KEY,
                 file_format_service: baseinjectorkeys.FILE_FORMAT_SERVICE,
                 filter_expression_builder:
                 baseinjectorkeys.DOCUMENT_FILTER_EXPRESSION_BUILDER_KEY):
        # pylint: disable=too-many-arguments
        BaseRecordService.__init__(self, dokument_dao, filter_expression_builder)
        self.document_file_info_dao = document_file_info_dao
        self.document_file_manager = document_file_manager
        self.document_type_dao = document_type_dao
        self.document_file_provider = document_file_provider
        self.ereignis_dao = ereignis_dao
        self.file_format_service = file_format_service
        
    def get_by_id(self, object_id):
        '''
        Just reaches through to the dao.
        '''
        file_info = self.document_file_info_dao.get_by_id(object_id)
        return self.dao.get_by_id(file_info.document_id)
                
    def add_document_file(self, document, file):
        '''
        Determines the file format (might result in an exception if the
        file format is not supported), then creates a new database entry
        for the file and finally moves the file to its correct location.
        '''
        
        file_format, resolution = self.file_format_service.get_format_and_resolution(file)
        file_info = self.document_file_info_dao.create_new_file_info(
            document.id,
            file_format,
            resolution)
        self._add_file_with_error_handling(file, file_info)
        
    def replace_document_file(self, file_info, file):
        '''
        Updates the format and resolution information in the database
        and moves the file to the place where it belongs. The existing
        file will be renamed to have .deleted as suffix. A former .deleted
        file will be overwritten.
        '''
        self.document_file_manager.delete_file(file_info)
        file_info.filetype, file_info.resolution = \
            self.file_format_service.get_format_and_resolution(file)
        self.document_file_info_dao.save(file_info)
        self._add_file_with_error_handling(file, file_info)

    def _add_file_with_error_handling(self, file, file_info):
        '''
        Helper method that tries to make as little mess as possible
        in the filesystem if something goes wrong.
        '''
        # pylint: disable=bare-except
        try:
            self.document_file_manager.add_file(file, file_info)
        except Exception as generic_exception:
            try:
                self.document_file_manager.delete_file(file_info)
            except:
                pass
            self.document_file_info_dao.delete(file_info.id)
            raise generic_exception

    def delete_file(self, document_file_info):
        '''
        Just deletes one document file (and the pertaining database information).
        The document entry itself remains.
        '''
        self.document_file_manager.delete_file(document_file_info)
        self.document_file_info_dao.delete(document_file_info.id)

    # pylint: disable=arguments-differ
    def delete(self, document):
        '''
        Deletes all the document files and all the database information
        '''
        file_infos = self.document_file_info_dao.get_file_infos_for_document(document.id)
        for file_info in file_infos:
            self.document_file_manager.delete_file(file_info)
        self.dao.delete(document.id)

    def get_file_infos_for_document(self, document):
        '''
        Returns all the file infos for the given document (what else?).
        '''
        return self._update_resolutions(
            self.document_file_info_dao.get_file_infos_for_document(document.id))

    def get_file_info_by_id(self, file_info_id):
        '''
        Returns the file info for a given file id
        '''
        
        return self._update_resolution(self.document_file_info_dao.get_by_id(file_info_id))

    def get_file_for_file_info(self, file_info):
        '''
        Returns the path to the file described by the file_info
        '''
        
        return self.document_file_manager.get_file_path(file_info)
            
    def get_pdf(self, document):
        '''
        Returns the document pdf file as byte string
        '''
        return self.document_file_provider.get_pdf(document)
    
    def get_thumbnail(self, document_file_info):
        '''
        Returns a thumbnail for the document as byte string
        '''
        return self.document_file_provider.get_thumbnail(document_file_info)
    
    def get_display_image(self, document_file_info):
        '''
        Returns a graphical representation of the document as byte string
        '''
        return self.document_file_provider.get_display_image(document_file_info)

    def create_new(self):
        '''
        Just calls the document constructor to get a new Document entity.
        '''
        # pylint: disable=no-self-use
        document = Document()
        document.document_type = self.document_type_dao.get_by_id(1)
        return document
    
    def _update_resolution(self, file_info):
        '''
        The resolution information in the database is not complete (due to
        historical reasons). This is an auxiliary method to correct this
        until the database is cleaned up.
        '''
        if not file_info.resolution is None:
            return file_info
        
        if file_info.filetype == 'gif':
            # More historical debt: gif files always have a resolution of 72 dpi,
            # but in the early days we scanned with 300 dpi and saved them as gif,
            # so the gif seems to be too large. So in fact we have to interpret
            # the resolution as 300
            file_info.resolution = get_gif_file_resolution(None)
            return file_info
        
        if file_info.filetype in ('jpg', 'png', 'tif'):
            try:
                file_path = self.document_file_manager.get_file_path(file_info)
            except DocumentFileNotFound:
                return self._set_default_resolution(file_info)

            file_info.resolution = get_graphic_file_resolution(file_path)
            if not file_info.resolution:
                file_info = self._set_default_resolution(file_info)
        
        return file_info
    
    # pylint: disable=no-self-use    
    def _set_default_resolution(self, file_info):    
        if file_info.filetype == 'jpg':
            file_info.resolution = 72
        else:
            file_info.resolution = 300
        return file_info
        
    def _update_resolutions(self, file_info_list):
        updated_list = []
        for file_info in file_info_list:
            updated_list.append(self._update_resolution(file_info))
        return updated_list

class DocumentTypeService(object):
    '''
    classdocs
    '''

    @inject
    def __init__(self, document_type_dao: baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY):
        '''
        Constructor
        '''
        self.document_type_dao = document_type_dao
        
    def get_document_type_dict(self):
        '''
        Returns all document types in form of a dictionary.
        '''
        type_dict = {}
        types = self.document_type_dao.get_all()
        for document_type in types:
            type_dict[document_type.description.upper()] = document_type
        return type_dict

    def get_document_types(self):
        '''
        Returns all document types as a dictionary with
        the document type id as key and the document type description
        as value.
        '''
        type_dict = {}
        types = self.document_type_dao.get_all()
        for document_type in types:
            type_dict[document_type.id] = document_type.description
        return type_dict
    
    def get_by_id(self, doc_type_id):
        '''
        Fetches a single document type by id.
        '''
        return self.document_type_dao.get_by_id(doc_type_id)

class EventService(BaseRecordService):
    '''
    Service for event handling. Most of the calls are just
    passed through to the daos.
    '''

    @inject
    def __init__(self,
                 ereignis_dao: baseinjectorkeys.EVENT_DAO_KEY,
                 filter_expression_builder: baseinjectorkeys.EVENT_FILTER_EXPRESSION_BUILDER_KEY,
                 event_crossreferences_dao: baseinjectorkeys.EVENT_CROSS_REFERENCES_DAO_KEY,
                 event_type_dao: baseinjectorkeys.EVENT_TYPE_DAO_KEY):
        BaseRecordService.__init__(self, ereignis_dao, filter_expression_builder)
        self.event_crossreferences_dao = event_crossreferences_dao
        self.event_type_dao = event_type_dao

    def get_events_for_date(self, alex_date):
        '''
        Returns all events that have the given start date
        '''
        return self.dao.get_events_for_date(alex_date)

    def get_cross_references(self, event):
        '''
        Returns all events that are crossreferenced to the given event.
        '''
        if event is None:
            return []
        crossreference_ids = self.event_crossreferences_dao.get_cross_references(event.id)
        events = []
        for crossreference_id in crossreference_ids:
            events.append(self.dao.get_by_id(crossreference_id))
        return events

    def remove_cross_reference(self, event1, event2):
        '''
        Removes the crossreference between the given two events.
        '''
        self.event_crossreferences_dao.remove_cross_reference(event1.id, event2.id)

    def add_cross_reference(self, event1, event2):
        '''
        Crossreferences the two given events.
        '''
        self.event_crossreferences_dao.add_cross_reference(event1.id, event2.id)

    def create_new(self, date_range):
        '''
        Creates a new event object for the given date range.
        '''
        # pylint: disable=no-self-use
        event = Event()
        event.daterange = date_range
        return event
    
    # pylint: disable=arguments-differ
    def delete(self, event):
        self.dao.delete(event.id)
        
    def get_event_types(self, event):
        '''
        Fetches the event types registered for the given event.
        '''
        return self.event_type_dao.get_event_types_for_event_id(event.id)
    
    def add_event_type(self, event, event_type):
        '''
        Registers a new event type for the given event.
        '''
        self.event_type_dao.join_event_type_to_event_id(event.id, event_type)
    
    def remove_event_type(self, event, event_type):
        '''
        Removes an event type from the list of event
        types registered with the given event.
        '''
        self.event_type_dao.unlink_event_type_from_event_id(event.id, event_type)
        
    def get_event_type_tree(self):
        '''
        Returns all event types wrapped into a tree object.
        '''
        entities = self.event_type_dao.find_all()
        entities.append(
            EventType(EventTypeIdentifier(0, 0), 
                      _("Event types")))

        return Tree(entities)

class FileFormatService:
    '''
    Check service for file types.
    
    Checks if the file type is supported, and when it is an
    image file, determines the resolution and checks if it is
    allowed. 
    
    The service may be configured overwriting the properties
    supported_formats, format_aliases, resolution_handlers and
    allowed resolutions 
    '''
    @inject
    def __init__(self, config: baseinjectorkeys.CONFIG_KEY):
        self.supported_formats = config.filetypes
        self.format_aliases = config.filetypealiases
        
        # TODO: Also put these options into the configuration
        self.resolution_handlers = {'tif': get_graphic_file_resolution,
                                    'jpg': get_graphic_file_resolution,
                                    'png': get_graphic_file_resolution,
                                    'gif': get_gif_file_resolution}
        self.allowed_resolutions = {'tif': [300, 400]}

    def get_format_and_resolution(self, file):
        '''
        Determines the file format and, if it
        is a graphics format, the resolution.
        '''
        fileformat = self._get_file_format(file)
        resolution = self._get_file_resolution(file, fileformat)
        return fileformat, resolution
    
    def _get_file_format(self, file):
        '''
        Determines the format and checks if it is supported.
        If not, an UnsupportedFileFormat exception is raised.
        '''
        # pylint: disable=unused-variable
        filename, file_extension = os.path.splitext(file) # @UnusedVariable
        fileformat = file_extension[1:].lower()
        if fileformat in self.format_aliases:
            fileformat = self.format_aliases[fileformat]
        if not fileformat in self.supported_formats:
            raise UnsupportedFileFormat(fileformat)
        return fileformat
    
    def _get_file_resolution(self, file, fileformat):
        '''
        Determines the file resolution (if appropriate). Raises
        an UnsupportedFileResolution exception, if it violates
        the configured constraints.
        '''
        resolution = None
        if fileformat in self.resolution_handlers:
            resolution = self.resolution_handlers[fileformat](file)
        if fileformat in self.allowed_resolutions:
            if not resolution in self.allowed_resolutions[fileformat]:
                raise UnsupportedFileResolution(fileformat, resolution)
        return resolution

class ReferenceService:
    '''
    Service for handling references to the main records.
    '''
    
    @inject
    def __init__(self,
                 event_dao: baseinjectorkeys.EVENT_DAO_KEY, 
                 document_dao: baseinjectorkeys.DOCUMENT_DAO_KEY, 
                 references_dao: baseinjectorkeys.RELATIONS_DAO_KEY):
        '''
        Used for injection.
        '''
        self.event_dao = event_dao
        self.document_dao = document_dao
        self.references_dao = references_dao
        
    def get_events_referenced_by_document(self, document):
        '''
        Returns the events that are related to a document.
        '''
        event_ids = self.references_dao.fetch_ereignis_ids_for_dokument_id(document.id)
        events = []
        for event_id in event_ids:
            events.append(self.event_dao.get_by_id(event_id))
        return events

    def get_documents_referenced_by_event(self, event):
        '''
        Returns the documents that are related to an event.
        '''
        document_ids = self.references_dao.fetch_document_ids_for_event_id(event.id)
        documents = []
        for document_id in document_ids:
            documents.append(self.document_dao.get_by_id(document_id))
        return documents

    def link_document_to_event(self, document, event):
        '''
        Creates a reference between a document and an event.
        '''
        self.references_dao.join_document_id_with_event_id(document.id, event.id)
    
    def delete_document_event_relation(self, document, event):
        '''
        Removes the reference between a document and an event.
        '''
        self.references_dao.delete_document_event_relation(document.id, event.id)

class ServiceModule(Module):
    '''
    Injector module for the services.
    '''
    
    def configure(self, binder):
        #dao_module = DaoModule()
        #dao_module.configure(binder)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                    ClassProvider(DocumentFileManager), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY,
                    ClassProvider(DocumentPdfGenerationService), scope=singleton)
        binder.bind(baseinjectorkeys.GRAPHICS_PDF_HANDLER_KEY,
                    ClassProvider(GraphicsPdfHandler), scope=singleton)
        binder.bind(baseinjectorkeys.TEXT_PDF_HANDLER_KEY,
                    ClassProvider(TextPdfHandler), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_SERVICE_KEY,
                    ClassProvider(EventService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_SERVICE_KEY,
                    ClassProvider(DocumentService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_TYPE_SERVICE_KEY,
                    ClassProvider(DocumentTypeService), scope=singleton)
        binder.bind(baseinjectorkeys.REFERENCE_SERVICE_KEY,
                    ClassProvider(ReferenceService), scope=singleton)
        binder.bind(baseinjectorkeys.FILE_FORMAT_SERVICE,
                    ClassProvider(FileFormatService), scope=singleton)
        binder.bind(baseinjectorkeys.CREATOR_SERVICE_KEY,
                    ClassProvider(CreatorService), scope=singleton)
        binder.bind(baseinjectorkeys.DATABASE_UPGRADE_SERVICE_KEY,
                    ClassProvider(DatabaseUpgradeService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_IMAGE_GENERATOR_KEY,
                    ClassProvider(DocumentFileImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.GRAPHICS_IMAGE_GENERATOR_KEY,
                    ClassProvider(GraphicsImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.TEXT_IMAGE_GENERATOR_KEY,
                    ClassProvider(TextImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.PDF_IMAGE_GENERATOR_KEY,
                    ClassProvider(PdfImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.MOVIE_IMAGE_GENERATOR_KEY,
                    ClassProvider(MovieImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY,
                    ClassProvider(PdfImageExtractor), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_PROVIDER,
                    ClassProvider(FileProvider), scope=singleton)

    @provider
    @inject
    def provide_pdf_handlers(self, 
                             graphics_handler: baseinjectorkeys.GRAPHICS_PDF_HANDLER_KEY,
                             text_handler: baseinjectorkeys.TEXT_PDF_HANDLER_KEY
                            ) -> baseinjectorkeys.PDF_HANDLERS_KEY:
        '''
        Returns the handlers to create pdf representations for certain
        file types.
        '''
        # pylint: disable=no-self-use
        
        return {'jpg': graphics_handler,
                'tif': graphics_handler,
                'gif': graphics_handler,
                'txt': text_handler}

    @provider
    @inject
    def provide_image_generators(self,
                                 graphics_image_generator:
                                 baseinjectorkeys.GRAPHICS_IMAGE_GENERATOR_KEY,
                                 text_image_generator:
                                 baseinjectorkeys.TEXT_IMAGE_GENERATOR_KEY,
                                 pdf_image_generator:
                                 baseinjectorkeys.PDF_IMAGE_GENERATOR_KEY,
                                 movie_image_generator:
                                 baseinjectorkeys.MOVIE_IMAGE_GENERATOR_KEY
                                ) -> baseinjectorkeys.IMAGE_GENERATORS_KEY:
        '''
        Returns the handlers for graphic images
        '''
        # pylint: disable=no-self-use
        
        return {'jpg': graphics_image_generator,
                'tif': graphics_image_generator,
                'gif': graphics_image_generator,
                'txt': text_image_generator,
                'pdf': pdf_image_generator,
                'mpg': movie_image_generator,
                'mp4': movie_image_generator,
                }
