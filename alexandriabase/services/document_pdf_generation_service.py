'''
Created on 07.05.2016

@author: michael
'''
import codecs
import re
from io import BytesIO
from injector import inject
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Image
from reportlab.platypus.paragraph import Paragraph
from PyPDF2.merger import PdfFileMerger

from alexandriabase import baseinjectorkeys

# Patching PyPDF2
# pylint: disable=wrong-import-order
# pylint: disable=ungrouped-imports
import PyPDF2.utils as utils
from PyPDF2.generic import DictionaryObject, readObject
from PyPDF2.pdf import ContentStream
from PyPDF2.utils import readNonWhitespace, b_

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
        
        image = Image(file)
        if image.imageWidth > available_width or image.imageHeight > available_height:
            # scale down to 
            factor = available_width / image.imageWidth
            height_factor = available_height / image.imageHeight
            if height_factor < factor:
                factor = height_factor
            story.append(Image(file, image.imageWidth*factor, image.imageHeight*factor))
        else:
            # calculate size
            resolution = file_info.resolution
            if not resolution:
                resolution = 300.0
            width_in_inch = image.imageWidth / resolution
            height_in_inch = image.imageHeight / resolution
            story.append(Image(file, width_in_inch * inch, height_in_inch * inch))
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
