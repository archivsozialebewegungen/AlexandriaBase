'''
Created on 28.02.2015

@author: michael
'''

import os.path
import re
import shutil
import struct
from io import BytesIO
import tempfile
from subprocess import call
import PyPDF2

from injector import inject
from PIL import Image, ImageFont, ImageDraw
from alexandriabase import baseinjectorkeys, get_font_dir
import logging
from PyPDF2.utils import PdfReadError

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
    @inject(document_file_manager=baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
            document_file_info_dao=baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
            document_pdf_generator=baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY,
            document_file_image_generator=baseinjectorkeys.DOCUMENT_FILE_IMAGE_GENERATOR_KEY)
    def __init__(self,
                 document_file_manager, 
                 document_file_info_dao,
                 document_pdf_generator,
                 document_file_image_generator):
        
        self.document_file_manager = document_file_manager
        self.document_file_info_dao = document_file_info_dao
        self.document_pdf_generator = document_pdf_generator
        self.document_file_image_generator = document_file_image_generator
        
    def get_pdf(self, document):
        '''
        Returns (and creates if necessary) the pdf file for a document.
        '''
        document_file_info = self.document_file_info_dao.get_by_id(document.id)
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
        font = ImageFont.truetype(os.path.join(get_font_dir(), "Arial_Bold.ttf"), 48)
        draw = ImageDraw.Draw(img)
        draw.text((10,60), "Keine Vorschau", font=font, fill=0)
        draw.text((10,120), "für Datei", font=font, fill=0)
        draw.text((10,180), document_file_info.get_file_name(), font=font, fill=0)
        return img

    def _create_no_display_image(self, document_file_info):
        img = Image.new('P', (400, 440), color=255)
        font = ImageFont.truetype(os.path.join(get_font_dir(), "Arial_Bold.ttf"), 48)
        draw = ImageDraw.Draw(img)
        draw.text((10,60), "Keine Graphik", font=font, fill=0)
        draw.text((10,120), "für Datei", font=font, fill=0)
        draw.text((10,180), document_file_info.get_file_name(), font=font, fill=0)
        return img
        
class DocumentFileImageGenerator:
    '''
    Main class for image generation. There are handlers for different
    file types to create an image (there should be more). Throws a
    NoImageGeneratorError if it is no possible to create an image from
    a file.
    '''
    
    @inject(image_generators=baseinjectorkeys.IMAGE_GENERATORS_KEY)
    def __init__(self, image_generators):
        
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
 
    @inject(document_file_manager=baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY)
    def __init__(self, document_file_manager):   
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
    
    @inject(document_file_manager=baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
            pdf_image_extractor=baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY)
    def __init__(self, document_file_manager, pdf_image_extractor):
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
    
    @inject(pdf_image_extractor=baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY,
            pdf_generator=baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY)
    def __init__(self, pdf_image_extractor, pdf_generator):
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
    
    @inject(document_file_manager=baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY)
    def __init__(self, document_file_manager):   
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
        # pylint: disable=bare-except

        try:
            pdf_reader = PyPDF2.PdfFileReader(open(path, "rb"))
        except Exception as error:
            self.logger.debug("Trying ghostscript due to pyPDF2 read failure (%s)." % error)
            return self._extract_using_ghostscript(path)
            
        if pdf_reader.isEncrypted:
            self.logger.debug("Trying ghostscript on encrypted pdf.")
            return self._extract_using_ghostscript(path)

        try:
            page0 = pdf_reader.getPage(0)
        except Exception as error:
            self.logger.debug("Trying ghostscript due to page read failure (%s)." % error)
            return self._extract_using_ghostscript(path)
            
        try:
            page_text = page0.extractText()
        except Exception as error:
            self.logger.debug("Trying ghostscript due to error extracting text from pdf (%s)." % error)
            return self._extract_using_ghostscript(path)

        if page_text != '':
            return self._extract_using_ghostscript(path)
        
        image_objects = self._find_image_objects(page0)
        if len(image_objects) != 1:
            # If we have zero images, we need to use ghostscript
            # If there are several images, it is too complicated to join them
            self.logger.debug("Using ghostscript (number of extractable images is %d)." % len(image_objects))
            return self._extract_using_ghostscript(path)
        
        image_object = image_objects[0]
        try:
            filter_type = image_object["/Filter"]
            if not isinstance(filter_type, list):
                filter_type = (filter_type,)
            for handler_key in self.data_extractors:
                if handler_key in filter_type:
                    self.logger.debug("Extracting for filter type %s" % filter_type)
                    return self.data_extractors[handler_key](image_object)
        except Exception as error:
            if self.logger.getEffectiveLevel() == logging.DEBUG:
                self.logger.exception("Exception running extractor (%s)." % error)
            # We really don't care what went wrong
            pass

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
        
        stdio =open(os.devnull, 'wb')
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
                       b'II',  # Byte order indication: Little indian
                       42,  # Version number (always 42)
                       8,  # Offset to first IFD
                       8,  # Number of tags in IFD
                       256, 4, 1, width,  # ImageWidth, LONG, 1, width
                       257, 4, 1, height,  # ImageLength, LONG, 1, lenght
                       258, 3, 1, 1,  # BitsPerSample, SHORT, 1, 1
                       259, 3, 1, compression,  # Compression, SHORT, 1, 4 = CCITT Group 4 fax encoding
                       262, 3, 1, 0,  # Threshholding, SHORT, 1, 0 = WhiteIsZero
                       273, 4, 1, struct.calcsize(tiff_header_struct),  # StripOffsets, LONG, 1, len of header
                       278, 4, 1, height,  # RowsPerStrip, LONG, 1, lenght
                       279, 4, 1, data_size,  # StripByteCounts, LONG, 1, size of image
                       0  # last IFD
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
        tiff_header = self._generate_tiff_header_for_ccitt_fax(width, height, len(data), compression)
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
            self.logger.debug("PdfReadError: %s" % error)
            return image_objects

        x_object = page['/Resources']['/XObject'].getObject()

        for obj in x_object:
            if '/Subtype' in x_object[obj] and x_object[obj]['/Subtype'] == '/Image':
                image_objects.append(x_object[obj])
        return image_objects

class DocumentFileManager(object):
    '''
    A simple class to manage document files. It provides
    all the methods needed to create, delete or find files
    referenced by a document file info.
    It also supports handling of derived files (pdfs, thumbnails etc.)
    '''
    # pylint: disable=no-self-use
    @inject(config_service=baseinjectorkeys.CONFIG_KEY,
            document_file_info_dao=baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY)
    def __init__(self, config_service, document_file_info_dao):
        '''
        Constructor reads the configuration from the config_service
        '''
        self.base_dir = config_service.document_dir
        self.archives = config_service.archive_dirs
        self.document_file_info_dao = document_file_info_dao
        self.path_handler = {THUMBNAIL: self._get_thumb_path,
                             DISPLAY_IMAGE: self._get_display_path,
                             DOCUMENT_PDF: self._get_pdf_path}
        self.logger = logging.getLogger("alexandriabase.services.documentfilemanager.DocumentFileManager")

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
        self.logger.debug("Searching for file %s" % document_file_info)
        basedir_path = self._create_basedir_path(document_file_info)
        
        self.logger.debug("Searching in %s" % basedir_path)
        if os.path.isfile(basedir_path):
            return basedir_path

        expanded_short_path = self._create_archive_sub_path(document_file_info)

        for archive in self.archives:
            archive_path = os.path.join(archive, expanded_short_path)
            self.logger.debug("Searching in %s" % archive_path)
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
