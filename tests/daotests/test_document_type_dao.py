'''
Created on 11.10.2015

@author: michael
'''
import unittest

from alexandriabase.base_exceptions import NoSuchEntityException
from alexandriabase.daos.documenttypedao import DocumentTypeDao
from alexandriabase.domain import DocumentType
from daotests.test_base import DatabaseBaseTest


class TestDocumentTypeDao(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        self.dao = DocumentTypeDao(self.engine)
        self.dao.clear_cache()

    def tearDown(self):
        self.dao.clear_cache()
        super().tearDown()

    def test_find_by_id(self):
        
        self.assertEqual(len(self.dao.cache), 0)
        document_type = self.dao.get_by_id(1)
        self.assertEqual(document_type.description, "Nicht bestimmt")
        self.assertEqual(self.dao.cache[1], document_type)
        exception_thrown = False
        try:
            document_type = self.dao.get_by_id(1234)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown)

    def test_cache_usage(self):
        
        dummy = DocumentType(7)
        dummy.description = "Plakat"
        self.dao.cache[dummy.id] = dummy

        document_type = self.dao.get_by_id(7)
        self.assertEqual(document_type.description, "Plakat")
        
    def test_cache_deletion(self):
        
        self.dao.get_by_id(3)
        self.assertTrue(3 in self.dao.cache)
        self.dao.delete(3)
        self.assertFalse(3 in self.dao.cache)
        
    def test_get_all(self):
        
        document_types = self.dao.get_all()
        self.assertEqual(20, len(document_types))




if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()