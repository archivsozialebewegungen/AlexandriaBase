'''
Created on 02.11.2015

@author: michael
'''
import unittest

from alexandriabase.base_exceptions import NoSuchEntityException
from daotests.test_base import DatabaseBaseTest
from alexandriabase.daos import CreatorDao, BasicCreatorProvider,\
    DocumentFileInfoDao, DocumentTypeDao, DocumentDao


class DocumentFileInfoDaoTest(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        self.creator_dao = CreatorDao(self.engine)
        self.creator_provider = BasicCreatorProvider(self.creator_dao)
        self.dao = DocumentFileInfoDao(self.engine, self.creator_provider)
        self.document_type_dao = DocumentTypeDao(self.engine)
        self.document_dao = DocumentDao(
            self.engine,
            None,
            self.creator_dao,
            self.document_type_dao,
            BasicCreatorProvider(self.creator_dao))

    def testGetByIdI(self):
        info = self.dao.get_by_id(2)
        self.assertEqual(info.document_id, 1)
        self.assertEqual(info.resolution, 400)
        self.assertEqual(info.filetype, 'tif')
        self.assertEqual(info.page, 3)
        
    def testGetByIdII(self):
        # Edge case: info does not exist
        exception_thrown = False
        try:
            self.dao.get_by_id(1234)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown)

    def testGetFileInfosForDocument(self):
        infos = self.dao.get_file_infos_for_document(1)
        self.assertEqual(len(infos),3)
        
    def testCreateNewFileInfoForDocument(self):
        info = self.dao.create_new_file_info(1)
        self.assertEqual(info.page, 4)
        self.assertEqual(info.id, 15)
        self.assertEqual(info.resolution, None)
        self.assertEqual(info.filetype, None)
        self.assertEqual(info.document_id, 1)

    def testCreateNewFileInfoForDocumentWithoutFiles(self):
        for info in self.dao.get_file_infos_for_document(1):
            self.dao.delete(info.id)
        infos = self.dao.get_file_infos_for_document(1)
        self.assertEqual(0, len(infos))
        info = self.dao.create_new_file_info(1)
        self.assertEqual(info.page, 1)
        self.assertEqual(info.id, 1)
        self.assertEqual(info.resolution, None)
        self.assertEqual(info.filetype, None)
        self.assertEqual(info.document_id, 1)


    def testDeleteI(self):
        # Default: separate document info record 
        self.dao.delete(2)
        exception_thrown = False
        try:
            self.dao.get_by_id(2)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown, "Info has not been deleted!")
        infos = self.dao.get_file_infos_for_document(1)
        self.assertEqual(len(infos),2)

    def testDeleteII(self):
        # Edge case: document record and document_info record are the same
        self.dao.delete(1)
        exception_thrown = False
        try:
            self.dao.get_by_id(1)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown, "Info has not been deleted!")
        try:
            self.document_dao.get_by_id(1)
            exception_thrown = False
        except NoSuchEntityException:
            exception_thrown = True
        self.assertFalse(exception_thrown, "Document itself has been deleted!")

    def testDeleteIII(self):
        # Edge case: Non existing id 
        self.dao.delete(12345)
        exception_thrown = False
        try:
            self.dao.get_by_id(12345)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown, "Info has not been deleted!")

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()