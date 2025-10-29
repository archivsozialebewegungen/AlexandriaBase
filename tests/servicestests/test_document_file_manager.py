'''
Created on 28.02.2015

@author: michael
'''
import os.path
import shutil
import unittest
import sys

from io import BytesIO
from alex_test_utils import get_testfiles_dir, TestEnvironment, MODE_FULL,\
    get_pdf_samples_dir
from alexandriabase.domain import DocumentFileInfo, Document
from alexandriabase.services import DocumentFileManager, \
    DocumentFileNotFound, PdfImageExtractor, THUMBNAIL, DISPLAY_IMAGE, DOCUMENT_PDF,\
    FileProvider, DocumentFileImageGenerator, GraphicsImageGenerator,\
    PdfImageGenerator, TextImageGenerator, MovieImageGenerator,\
    ImageExtractionFailure, GraphicsPdfHandler, TextPdfHandler,\
    DocumentPdfGenerationService
from unittest.mock import MagicMock
import logging
from alexandriabase.daos import DocumentFileInfoDao

manual_test = True

class FileProviderTests(unittest.TestCase):

    def setUp(self):
        self.env = TestEnvironment(mode=MODE_FULL)
        self.document_file_info_dao = MagicMock(spec=DocumentFileInfoDao)
        self.document_file_manager = DocumentFileManager(self.env.config, self.document_file_info_dao)
        self.graphics_pdf_handler = GraphicsPdfHandler(self.document_file_manager)
        self.txt_pdf_handler = TextPdfHandler(self.document_file_manager)
        self.document_pdf_generation_service = DocumentPdfGenerationService(
            self.document_file_info_dao,
            self.document_file_manager,
            {'jpg': self.graphics_pdf_handler,
             'tif': self.graphics_pdf_handler,
             'gif': self.graphics_pdf_handler,
             'txt': self.txt_pdf_handler})
        self.graphics_image_generator = GraphicsImageGenerator(self.document_file_manager)
        self.pdf_image_extractor = PdfImageExtractor()
        self.pdf_image_generator = PdfImageGenerator(self.document_file_manager,
                                                     self.pdf_image_extractor)
        self.movie_image_generator = MovieImageGenerator(self.document_file_manager)
        self.txt_image_generator = TextImageGenerator(self.pdf_image_extractor,
                                                      self.document_pdf_generation_service,
                                                      )
        self.document_file_image_generator = DocumentFileImageGenerator(
            {'jpg': self.graphics_image_generator,
             'tif': self.graphics_image_generator,
             'gif': self.graphics_image_generator,
             'pdf': self.pdf_image_generator,
             'txt': self.txt_image_generator,
             'mpg': self.movie_image_generator})
        self.file_provider = FileProvider(self.document_file_manager,
                                          self.document_file_info_dao,
                                          self.document_pdf_generation_service,
                                          self.document_file_image_generator)
        
        
    def tearDown(self):
        self.env.cleanup()

    def test_pdf_generation(self):
        
        document = Document(1)
        self.document_file_info_dao.get_by_id.return_value = self.env.document_file_infos[1]
        self.document_file_info_dao.get_file_infos_for_document.return_value = [self.env.document_file_infos[1],
                                                                                self.env.document_file_infos[3],
                                                                                self.env.document_file_infos[2]]
        cache_path = self.document_file_manager.get_generated_file_path(self.env.document_file_infos[1], DOCUMENT_PDF)
        self.assertFalse(os.path.exists(cache_path))
        
        pdf = self.file_provider.get_pdf(document)
        self.assertFalse(pdf is None)
        self.assertEqual(b'%PDF-1.3', pdf[0:8])
        
        self.assertTrue(os.path.exists(cache_path))
        
    def test_thumbnail_generation_tif(self):
        
        thumbnail = self.file_provider.get_thumbnail(self.env.document_file_infos[1])
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])

        thumbnail2 = self.document_file_manager.get_generated_file(self.env.document_file_infos[1], THUMBNAIL)
        
        self.assertEqual(thumbnail, thumbnail2)

        # Checks that creating thumbnail dir works if it already exists
        self.file_provider.get_thumbnail(self.env.document_file_infos[2])
        
    def test_thumbnail_generation_jpg(self):
        
        thumbnail = self.file_provider.get_thumbnail(self.env.document_file_infos[6])
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])


    def test_thumbnail_generation_pdf(self):

        thumbnail = self.file_provider.get_thumbnail(self.env.document_file_infos[8])
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])

    def test_thumbnail_generation_txt(self):

        thumbnail = self.file_provider.get_thumbnail(self.env.document_file_infos[11])
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])

    @unittest.skipIf(os.path.basename(sys.argv[0]) == 'nosetests', "Can't run on travis because ffmpeg needs to be installed")
    def test_thumbnail_generation_mpg(self):

        thumbnail = self.file_provider.get_thumbnail(self.env.document_file_infos[13])
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])

    def test_thumbnail_generation_unsupported_filetype(self):

        document_file_manager = MagicMock(spec=DocumentFileManager)
        document_file_manager.get_generated_file.side_effect = FileNotFoundError()
        self.file_provider = FileProvider(document_file_manager,
                                          self.document_file_info_dao,
                                          self.document_pdf_generation_service,
                                          self.document_file_image_generator)

        document_file_info = DocumentFileInfo(27)
        document_file_info.filetype = 'xls'
        thumbnail = self.file_provider.get_thumbnail(document_file_info)
        
        self.assertEqual(b'\x89PNG\r\n', thumbnail[0:6])


    def test_display_image_generation_tif(self):
        
        display_image = self.file_provider.get_display_image(self.env.document_file_infos[1])
        
        self.assertEqual(b'\x89PNG\r\n', display_image[0:6])

        display_image2 = self.document_file_manager.get_generated_file(self.env.document_file_infos[1], DISPLAY_IMAGE)
        
        self.assertEqual(display_image, display_image2)

        # Checks that creating thumbnail dir works if it already exists
        self.file_provider.get_display_image(self.env.document_file_infos[2])

    def test_display_image_generation_unsupported_filetype(self):

        document_file_manager = MagicMock(spec=DocumentFileManager)
        document_file_manager.get_generated_file.side_effect = FileNotFoundError()
        self.file_provider = FileProvider(document_file_manager,
                                          self.document_file_info_dao,
                                          self.document_pdf_generation_service,
                                          self.document_file_image_generator)
        document_file_info = DocumentFileInfo(27)
        document_file_info.filetype = 'xls'
        display_image = self.file_provider.get_display_image(document_file_info)
        
        self.assertEqual(b'\x89PNG\r\n', display_image[0:6])

#@unittest.skipUnless(os.path.basename(sys.argv[0]) == 'nosetests', "Running just on a complete test run")
class PdfImageExtractorTests(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler(os.devnull)
        logger.addHandler(handler)
        self.dir = get_pdf_samples_dir()
        self.extractor = PdfImageExtractor()
        
    def test_all_sample_files(self):
        
        unreadable_files = ('PYPDF2_PAGE_READERROR.pdf',)
        
        for filename in os.listdir(self.dir):
            if filename in unreadable_files:
                continue
            img = self.extractor.extract_image(os.path.join(self.dir, filename))
            file_buffer = BytesIO()
            img.save(file_buffer, 'png')
            self.assertEqual(b'\x89PNG\r\n', file_buffer.getvalue()[0:6])
        
        for filename in unreadable_files:
            expected_exception = False
            try:
                img = self.extractor.extract_image(os.path.join(self.dir, filename))
            except ImageExtractionFailure:
                expected_exception = True
            self.assertTrue(expected_exception)
    
class DocumentFileManagerTests(unittest.TestCase):

    def setUp(self):
        self.env = TestEnvironment(mode=MODE_FULL)
        self.document_file_info_dao = MagicMock(spec=DocumentFileInfoDao)
        self.document_file_manager = DocumentFileManager(self.env.config, self.document_file_info_dao)
        
    def tearDown(self):
        self.env.cleanup()

    def testConstructor(self):
        self.assertEqual(self.document_file_manager.base_dir, self.env.document_dir)
        self.assertEqual(self.document_file_manager.archives, self.env.archive_dirs)
        
    def test_get_file_path_for_non_existing_file(self):    
        document_file_info = DocumentFileInfo(2)
        document_file_info.filetype = "txt"
        exception_raised = False
        try:
            self.document_file_manager.get_file_path(document_file_info)
        except DocumentFileNotFound:
            exception_raised = True
        self.assertTrue(exception_raised)
        
    def test_get_file_path(self):
        file_info = DocumentFileInfo(5)
        file_info.filetype = "txt"
        file_path = self.document_file_manager.get_file_path(file_info)
        self.assertEqual(file_path, self.env.file_paths[5])
        
        file_info = DocumentFileInfo(6)
        file_info.filetype = "jpg"
        file_path = self.document_file_manager.get_file_path(file_info)
        self.assertEqual(file_path, self.env.file_paths[6])

        file_info = DocumentFileInfo(1)
        file_info.filetype = "tif"
        file_path = self.document_file_manager.get_file_path(file_info)
        self.assertEqual(file_path, self.env.file_paths[1])

    def test_get_thumb_path(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        thumb_path = self.document_file_manager.get_generated_file_path(file_info, THUMBNAIL)
        self.assertTrue("filestorage/archive/1000/tif/thumb/00000001.png" in thumb_path)
        
    def test_get_display_image_path(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        display_path = self.document_file_manager.get_generated_file_path(file_info, DISPLAY_IMAGE)
        self.assertTrue("filestorage/archive/1000/tif/display/00000001.png" in display_path)

    def test_get_pdf_path(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        file_info.document_id = 1
        pdf_path = self.document_file_manager.get_generated_file_path(file_info, DOCUMENT_PDF)
        self.assertTrue("filestorage/archive/1000/tif/pdf/00000001.pdf" in pdf_path)

    def test_get_pdf_path_2(self):
        document_file_info = DocumentFileInfo(1)
        document_file_info.filetype = 'tif'
        document_file_info.document_id = 1
        file_info = DocumentFileInfo(3)
        file_info.filetype = 'gif'
        file_info.document_id = 1
        self.document_file_info_dao.get_by_id.return_value = document_file_info
        pdf_path = self.document_file_manager.get_generated_file_path(file_info, DOCUMENT_PDF)
        self.assertTrue("filestorage/archive/1000/tif/pdf/00000001.pdf" in pdf_path)

    def test_get_pdf_path_3(self):
        document_file_info = DocumentFileInfo(8)
        document_file_info.filetype = 'pdf'
        document_file_info.document_id = 8
        self.document_file_info_dao.get_by_id.return_value = document_file_info
        pdf_path = self.document_file_manager.get_generated_file_path(document_file_info, DOCUMENT_PDF)
        self.assertTrue("filestorage/docs/pdf/pdf/00000008.pdf" in pdf_path)

    def test_add_new_file_existing_target_dir(self):
        target = os.path.join(self.env.tmpdir.name, "newtextfile.txt")

        shutil.copy(os.path.join(get_testfiles_dir(), "testfile.txt"), target)
        self.assertTrue(os.path.isfile(target))
        document_file_info = DocumentFileInfo(4711)
        document_file_info.filetype = 'txt'
        self.document_file_manager.add_file(target, document_file_info)
        self.assertFalse(os.path.isfile(target))
        self.assertEqual("txt", document_file_info.filetype)
        new_path = os.path.join(os.path.join(self.env.document_dir, "txt"), "00004711.txt")
        self.assertTrue(os.path.isfile(new_path))
    
    def test_add_new_file_non_existing_target_dir(self):
        target = os.path.join(self.env.tmpdir.name, "newjpgfile.jpg")

        shutil.copy(os.path.join(get_testfiles_dir(), "testfile.jpg"), target)
        self.assertTrue(os.path.isfile(target))
        document_file_info = DocumentFileInfo(4711)
        document_file_info.filetype = 'jpg'
        self.document_file_manager.add_file(target, document_file_info)
        self.assertFalse(os.path.isfile(target))
        self.assertEqual("jpg", document_file_info.filetype)
        new_path = os.path.join(os.path.join(self.env.document_dir, "jpg"), "00004711.jpg")
        self.assertTrue(os.path.isfile(new_path))

    def test_delete_document(self):

        for i in (5, 6, 1):        
            path_before = self.env.file_paths[i]
            path_after = "%s.deleted" % self.env.file_paths[i]

            self.assertTrue(os.path.isfile(path_before))
            self.assertFalse(os.path.isfile(path_after))
            self.document_file_manager.delete_file(self.env.document_file_infos[i])
            self.assertFalse(os.path.isfile(path_before))
            self.assertTrue(os.path.isfile(path_after))


    def test_delete_generated_file(self):
        
        document_file_info = self.env.document_file_infos[1]
        path = self.document_file_manager.get_generated_file_path(document_file_info, DOCUMENT_PDF)
        self.document_file_manager.delete_generated_file(document_file_info, DOCUMENT_PDF)
        self.assertFalse(os.path.exists(path))    

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
