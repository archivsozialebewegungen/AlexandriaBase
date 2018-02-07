'''
Created on 12.05.2016

@author: michael
'''
import os
import tempfile
import unittest
from unittest.mock import MagicMock, call

from alex_test_utils import get_testfiles_dir, TestEnvironment, MODE_FULL
from alexandriabase.domain import Document, DocumentFileInfo
from PyPDF2.pdf import PdfFileReader
from alexandriabase.services import DocumentFileManager, GraphicsPdfHandler,\
    TextPdfHandler, DocumentPdfGenerationService
from alexandriabase.daos import DocumentFileInfoDao

manual_check = False

class Test(unittest.TestCase):


    def setUp(self):
        
        self.env = TestEnvironment(mode=MODE_FULL)
        
        self.document_file_manager = MagicMock(spec=DocumentFileManager)
        self.document_file_info_dao = MagicMock(spec=DocumentFileInfoDao)
        self.graphics_pdf_handler = GraphicsPdfHandler(self.document_file_manager)
        self.txt_pdf_handler = TextPdfHandler(self.document_file_manager)
        handlers = {'jpg': self.graphics_pdf_handler,
             'tif': self.graphics_pdf_handler,
             'gif': self.graphics_pdf_handler,
             'txt': self.txt_pdf_handler}
        self.document_pdf_generation_service = DocumentPdfGenerationService(
            self.document_file_info_dao, self.document_file_manager, handlers)
        
        self.text_base_dir = os.path.join(
            os.path.join(
            os.path.join(get_testfiles_dir(), "filestorage"), "docs"), "txt")
        self.tmp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=not manual_check)

    def tearDown(self):
        self.env.cleanup()
        self.tmp_file.close()
        if manual_check:
            print("Now check file %s" % self.tmp_file.name)
        
    def testDocumentGeneration(self):

        doc = Document(1)

        self.document_file_info_dao.get_file_infos_for_document.return_value = [
            self.env.document_file_infos[1], # tif
            self.env.document_file_infos[3], # gif
            self.env.document_file_infos[8], # pdf
            self.env.document_file_infos[4]] # jpg

        values = {self.env.document_file_infos[1]: self.env.file_paths[1],
                  self.env.document_file_infos[3]: self.env.file_paths[3],
                  self.env.document_file_infos[8]: self.env.file_paths[8],
                  self.env.document_file_infos[4]: self.env.file_paths[4]}
        def side_effect(arg):
            return values[arg]

        self.document_file_manager.get_file_path.side_effect = side_effect
        pdf = self.document_pdf_generation_service.generate_document_pdf(doc)
        
        self.tmp_file.write(pdf)
        
        self.document_file_info_dao.get_file_infos_for_document.assert_called_with(1)
        self.document_file_manager.get_file_path.assert_has_calls(
            (call(self.env.document_file_infos[1]),
             call(self.env.document_file_infos[3]),
             call(self.env.document_file_infos[8]),
             call(self.env.document_file_infos[4])))
        
        file = open(self.tmp_file.name, "rb")
        reader = PdfFileReader(file)
        self.assertEqual(3, reader.getNumPages())
        

    def testMissingHandler(self):
        doc = Document(1)
        file_info = DocumentFileInfo(2)
        file_info.filetype = 'xls'

        self.document_file_info_dao.get_file_infos_for_document.return_value = [file_info]

        pdf = self.document_pdf_generation_service.generate_document_pdf(doc)
        self.tmp_file.write(pdf)
        
        self.document_file_info_dao.get_file_infos_for_document.assert_called_with(1)

    def testRealLifeTexts(self):
        doc = Document(5)
        file_info1 = DocumentFileInfo(5)
        file_info1.filetype = 'txt'
        file1 = os.path.join(self.text_base_dir, "00000005.txt")
        file_info2 = DocumentFileInfo(10)
        file_info2.filetype = 'txt'
        file2 = os.path.join(self.text_base_dir, "00000011.txt")
        file_info3 = DocumentFileInfo(11)
        file_info3.filetype = 'txt'
        file3 = os.path.join(self.text_base_dir, "00000012.txt")

        values = {file_info1: file1,
                  file_info2: file2,
                  file_info3: file3}
        def side_effect(arg):
            return values[arg]

        self.document_file_info_dao.get_file_infos_for_document.return_value = [file_info1, file_info2, file_info3]
        self.document_file_manager.get_file_path.side_effect = side_effect

        pdf = self.document_pdf_generation_service.generate_document_pdf(doc)
        self.tmp_file.write(pdf)
       
        self.document_file_info_dao.get_file_infos_for_document.assert_called_with(5)
        self.document_file_manager.get_file_path.assert_has_calls(
            (call(file_info1), call(file_info2), call(file_info3)))
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()