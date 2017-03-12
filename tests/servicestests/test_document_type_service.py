'''
Created on 01.04.2016

@author: michael
'''
import unittest
from unittest.mock import MagicMock, Mock

from alexandriabase.daos.documenttypedao import DocumentTypeDao
from alexandriabase.domain import DocumentType
from alexandriabase.services.documenttypeservice import DocumentTypeService


class DocumentTypeServiceTest(unittest.TestCase):

    def setUp(self):
        self.document_type_dao = MagicMock(spec=DocumentTypeDao)
        self.doc_type = DocumentType(1)
        self.doc_type.description = "My description"
        
        self.document_type_service = DocumentTypeService(self.document_type_dao)


    def tearDown(self):
        pass


    def test_get_document_type_dict(self):
        self.document_type_dao.get_all = Mock(return_value=(self.doc_type,))
        types = self.document_type_service.get_document_type_dict()
        self.assertEqual('My description', types['MY DESCRIPTION'].description)
        self.document_type_dao.get_all.assert_called_once_with()
        
    def test_get_document_types(self):
        self.document_type_dao.get_all = Mock(return_value=(self.doc_type,))
        types = self.document_type_service.get_document_types()
        self.assertEqual('My description', types[1])
        self.document_type_dao.get_all.assert_called_once_with()
        
    def test_get_by_id(self):
        self.document_type_dao.get_by_id = Mock(return_value=self.doc_type)
        type = self.document_type_service.get_by_id(25)
        self.assertEqual('My description', type.description)
        self.document_type_dao.get_by_id.assert_called_once_with(25)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()