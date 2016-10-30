'''
Created on 11.10.2015

@author: michael
'''
from sqlalchemy.sql.expression import select
import unittest

from alexandriabase.daos.metadata import DOCUMENT_TABLE
from alexandriabase.daos.relationsdao import DocumentEventRelationsDao
from alexandriabase.domain import AlexDate
from daotests.test_base import DatabaseBaseTest


class TestRelationsDao(DatabaseBaseTest):
    
    def setUp(self):
        super().setUp()
        self.dao = DocumentEventRelationsDao(self.engine)
        
    def tearDown(self):
        super().tearDown()
        
    def test_fetch_doc_file_ids_for_ereignis_id(self):
        result = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        self.assertTrue(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], 4)
    
        result = self.dao.fetch_doc_file_ids_for_event_id(1950000001)
        self.assertFalse(result)
        self.assertEqual(len(result), 0)
        
    def test_join_document_to_event(self):
        join_list = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        self.assertEqual(len(join_list), 2)
        self.assertIn(1, join_list)
        self.assertIn(4, join_list)
        
        self.dao.join_document_id_with_event_id(18, 1940000001)
        join_list = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        self.assertEqual(len(join_list), 3)
        self.assertIn(18, join_list)
        
        self.dao.join_document_id_with_event_id(1, 1940000001)
        join_list = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        # Should not be added again!
        self.assertEqual(len(join_list), 3)
        
    def test_remove_join_document_to_event(self):
        join_list = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        self.assertEqual(len(join_list), 2)
        self.dao.delete_document_event_relation(1, 1940000001)
        join_list = self.dao.fetch_doc_file_ids_for_event_id(1940000001)
        self.assertEqual(len(join_list), 1)
    
        
    def test_fetch_dokument_ids_for_ereignis_id(self):
        result = self.dao.fetch_document_ids_for_event_id(1940000001)
        self.assertTrue(result)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], 4)
    
        result = self.dao.fetch_document_ids_for_event_id(1950000001)
        self.assertFalse(result)
        self.assertEqual(len(result), 0)

    def test_fetch_ereignis_id_for_dokument_file_id(self):
        result = self.dao.fetch_ereignis_ids_for_dokument_id(4)
        self.assertTrue(result)
        self.assertEqual(len(result), 2)
        self.assertIn(1940000001, result)
        self.assertIn(1960013001, result)


    def test_fetch_doc_and_event_ids_I(self):
        
        references = self.dao.fetch_doc_event_references()
        self.assertEqual(7, len(references.keys()))
        self.assertEqual(2, len(references[4]))

    def test_fetch_doc_and_event_ids_II(self):
        
        references = self.dao.fetch_doc_event_references(start_date=AlexDate(1950))
        self.assertEqual(1, len(references.keys()))
        self.assertEqual(1, len(references[4]))
        self.assertIn(1960013001, references[4])
        self.assertIn(4, references)

    def test_fetch_doc_and_event_ids_III(self):
        
        references = self.dao.fetch_doc_event_references(end_date=AlexDate(1950))
        self.assertEqual(2, len(references.keys()))
        self.assertEqual(1, len(references[1]))
        self.assertEqual(1, len(references[4]))
        self.assertIn(1940000001, references[1])
        self.assertIn(1940000001, references[4])
        self.assertIn(1, references)
        self.assertIn(4, references)

    def test_fetch_doc_and_event_ids_IV(self):
        
        references = self.dao.fetch_doc_event_references(start_date=AlexDate(1945),
                                                                   end_date=AlexDate(1950))
        self.assertEqual(0, len(references.keys()))
    
    def test_fetch_doc_and_event_ids_V(self):
        
        references = self.dao.fetch_doc_event_references(location='1.1.ii')
        self.assertEqual(1, len(references.keys()))
        self.assertEqual(2, len(references[4]))
        self.assertIn(1940000001, references[4])
        self.assertIn(1960013001, references[4])
        self.assertIn(4, references)

    def test_fetch_doc_and_event_ids_VI(self):
        
        references = self.dao.fetch_doc_event_references(location='1.1.I')
        self.assertEqual(2, len(references.keys()))
        self.assertEqual(2, len(references[4]))
        self.assertIn(1940000001, references[4])
        self.assertIn(1960013001, references[4])
        self.assertIn(4, references)
        self.assertIn(1, references)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()