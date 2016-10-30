'''
Created on 21.10.2015

@author: michael
'''
import os
import unittest
from unittest.mock import MagicMock, call

from alex_test_utils import get_testfiles_dir, TestEnvironment, MODE_FULL
from alexandriabase.config import Config
from alexandriabase.daos.documentdao import DocumentDao, \
    DocumentFilterExpressionBuilder
from alexandriabase.daos.documentfileinfodao import DocumentFileInfoDao
from alexandriabase.daos.eventdao import EventDao
from alexandriabase.domain import Document, DocumentFileInfo
from alexandriabase.services.documentfilemanager import DocumentFileManager,\
    DocumentFileNotFound, FileProvider
from alexandriabase.services.documentservice import DocumentService
from alexandriabase.services.fileformatservice import FileFormatService
from alexandriabase.daos.documenttypedao import DocumentTypeDao

class DocumentServiceTest(unittest.TestCase):


    def setUp(self):
        self.env = TestEnvironment(mode=MODE_FULL)
        self.event_dao = MagicMock(spec=EventDao)
        self.document_dao = MagicMock(spec=DocumentDao)
        self.document_type_dao = MagicMock(spec=DocumentTypeDao)
        self.document_file_info_dao = MagicMock(spec=DocumentFileInfoDao)
        self.document_file_provider = MagicMock(spec=FileProvider)
        self.document_file_manager = MagicMock(spec=DocumentFileManager)
        self.config_service = Config()
        self.file_format_service = FileFormatService(self.env.config)
        self.filter_expression_builder = MagicMock(spec=DocumentFilterExpressionBuilder)
        self.service = DocumentService(
            self.document_dao,
            self.document_file_info_dao,
            self.document_file_manager,
            self.document_type_dao,
            self.document_file_provider,
            self.event_dao,
            self.file_format_service,
            self.filter_expression_builder)

    def test_get_nearest(self):
        self.service.get_nearest(56, None)
        self.document_dao.get_nearest.assert_called_once_with(56, None)

    def testDeleteDocumentFile(self):
        document = MagicMock(spec=Document)
        document.id = 45
        document_file_info = MagicMock(DocumentFileInfo)
        self.service.delete_file(document_file_info)
        self.document_file_info_dao.delete.assert_called_once_with(document_file_info.id)
        self.document_file_manager.delete_file.assert_called_once_with(document_file_info)
        
    def testDelete(self):
        
        document = Document(1)
        
        file_infos = []
        file_infos.append(DocumentFileInfo(2))
        file_infos.append(DocumentFileInfo(3))
        self.document_file_info_dao.get_file_infos_for_document = MagicMock(return_value=file_infos)
        self.document_dao.delete = MagicMock()
        
        self.service.delete(document)
        
        self.document_file_manager.delete_file.call_args_list = [call(file_infos[0]), call(file_infos[1])]
        self.document_dao.delete.assert_called_once_with(1)
        
    def test_get_file_infos_for_document(self):

        document = Document(1)
        self.document_file_info_dao.get_file_infos_for_document.return_value = [DocumentFileInfo(1)]
        file_infos = self.service.get_file_infos_for_document(document)
        self.assertEqual(1, len(file_infos))
        self.document_file_info_dao.get_file_infos_for_document.assert_called_once_with(1)
        
    def test_create_new(self):
        
        new_document = self.service.create_new()
        
        self.assertTrue(isinstance(new_document, Document))
        self.assertFalse(new_document.id)

    def test_add_document_file_working(self):
        
        test_file = os.path.join(get_testfiles_dir(), "testfile.jpg")
        document = Document(1)
        file_info = DocumentFileInfo(1)
        
        self.document_file_info_dao.create_new_file_info.return_value = file_info
        
        self.service.add_document_file(document, test_file)
        
        self.document_file_manager.add_file.assert_called_once_with(test_file, file_info)

    def test_replace_document_file_working(self):
        
        # Prepare input
        test_file = os.path.join(get_testfiles_dir(), "testfile.jpg")
        
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'gif'
        file_info.resolution = 72
        
        # Prepare mock
        self.document_file_info_dao.create_new_file_info.return_value = file_info
        
        # And action!
        self.service.replace_document_file(file_info, test_file)
        
        # Assert
        self.document_file_manager.delete_file.assert_called_once_with(file_info)
        self.document_file_info_dao.save.assert_called_once_with(file_info)
        self.document_file_manager.add_file.assert_called_once_with(test_file, file_info)
        self.assertEqual('jpg', file_info.filetype)
        self.assertEqual(400, file_info.resolution)

    def test_add_document_file_not_working(self):
        
        test_file = os.path.join(get_testfiles_dir(), "testfile.jpg")
        document = Document(1)
        file_info = DocumentFileInfo(1)
        
        self.document_file_info_dao.create_new_file_info.return_value = file_info
        self.document_file_manager.add_file.side_effect=FileNotFoundError()
        self.document_file_manager.delete_file.side_effect=Exception()
        
        exception_raised = False
        try:
            self.service.add_document_file(document, test_file)
        except FileNotFoundError:
            exception_raised = True
        self.assertTrue(exception_raised)
        
        self.document_file_manager.add_file.assert_called_once_with(test_file, file_info)
        self.document_file_manager.delete_file.assert_called_once_with(file_info)
        self.document_file_info_dao.delete.assert_called_once_with(file_info.id)

    def test_find_all_entities(self):

        self.document_dao.get_count.return_value = 5
        self.document_dao.find.return_value = [Document(1), Document(2), Document(3), Document(4), Document(5)]
        result = self.service.find(None, 1, 10)
        self.assertEqual(5, len(result.entities))
        self.assertEqual(1, result.number_of_pages)
        
    def test_find_paginated_entities(self):
        self.document_dao.get_count.return_value = 5
        self.document_dao.find.side_effect = ([Document(1), Document(4), Document(8)],
                                              [Document(11), Document(12)])
        result = self.service.find(None, 1, 3)
        self.assertEqual(3, len(result.entities))
        self.assertEqual(1, result.entities[0].id)
        self.assertEqual(4, result.entities[1].id)
        self.assertEqual(8, result.entities[2].id)
        self.assertEqual(2, result.number_of_pages)
        result = self.service.find(None, 2, 3)
        self.assertEqual(2, len(result.entities))
        self.assertEqual(11, result.entities[0].id)
        self.assertEqual(12, result.entities[1].id)
        self.assertEqual(2, result.number_of_pages)
        
    def test_find_paginated_entities_with_filter(self):
        self.document_dao.get_count.return_value = 4
        self.document_dao.find.side_effect = ([Document(4), Document(8)],
                                              [Document(11), Document(12)])
        where = "egal" 
        result = self.service.find(where, 1, 2)
        self.assertEqual(2, len(result.entities))
        self.assertEqual(4, result.entities[0].id)
        self.assertEqual(8, result.entities[1].id)
        self.assertEqual(2, result.number_of_pages)
        result = self.service.find(where, 2, 2)
        self.assertEqual(2, len(result.entities))
        self.assertEqual(11, result.entities[0].id)
        self.assertEqual(12, result.entities[1].id)
        self.assertEqual(2, result.number_of_pages)
        
    def test_update_resolution_gif(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'gif'
        self.service._update_resolution(file_info)
        self.assertEqual(300, file_info.resolution)
        
    def test_update_resolution_jpg(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'jpg'
        self.document_file_manager.get_file_path.return_value = self.env.jpg_file_path
        self.service._update_resolution(file_info)
        self.assertEqual(400, file_info.resolution)

    def test_update_resolution_missing_jpg(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'jpg'
        self.document_file_manager.get_file_path.side_effect=DocumentFileNotFound(file_info)
        self.service._update_resolution(file_info)
        self.assertEqual(72, file_info.resolution)

    def test_update_resolution_missing_tiff(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        self.document_file_manager.get_file_path.side_effect=DocumentFileNotFound(file_info)
        self.service._update_resolution(file_info)
        self.assertEqual(300, file_info.resolution)

    def test_update_resolution_tiff(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        self.document_file_manager.get_file_path.return_value = self.env.tif_file_path
        self.service._update_resolution(file_info)
        self.assertEqual(72.0, file_info.resolution)

    def test_no_resolution_update_necessary(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'tif'
        file_info.resolution = 666
        self.service._update_resolution(file_info)
        self.assertEqual(666, file_info.resolution)

    def test_get_file_info_by_id(self):
        file_info = DocumentFileInfo(1)
        file_info.filetype = 'gif'
        self.document_file_info_dao.get_by_id.return_value = file_info
        file_info = self.service.get_file_info_by_id(1)
        self.assertEqual(300, file_info.resolution)

    def test_get_pdf_file(self):
        document = Document(1)
        self.service.get_pdf(document)
        self.document_file_provider.get_pdf.assert_called_once_with(document)

    def test_get_thumbnail(self):
        document_file_info = DocumentFileInfo(1)
        self.service.get_thumbnail(document_file_info)
        self.document_file_provider.get_thumbnail.assert_called_once_with(document_file_info)

    def test_get_display_image(self):
        document_file_info = DocumentFileInfo(1)
        self.service.get_display_image(document_file_info)
        self.document_file_provider.get_display_image.assert_called_once_with(document_file_info)

    def test_get_by_id(self):
        self.document_dao.get_by_id.return_value = Document(4)
        document = self.service.get_by_id(4)
        self.assertEqual(4, document.id)

    def test_get_file_for_file_info(self):
        file_info = DocumentFileInfo(4)
        self.document_file_manager.get_file_path.return_value = "/some/path"
        path = self.service.get_file_for_file_info(file_info)
        self.assertEqual(path, "/some/path")
if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
