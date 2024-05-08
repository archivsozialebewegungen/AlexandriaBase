'''
Created on 11.10.2015

@author: michael
'''
import unittest

from alexandriabase.daos import EventCrossreferencesDao, EventDao, CreatorDao,\
    EventTypeDao, DocumentFilterExpressionBuilder, EventFilterExpressionBuilder,\
    DocumentEventRelationsDao
from daotests.test_base import DatabaseBaseTest
from alexandriabase.domain import DocumentEventReferenceFilter


class TestDocumentEventReferencesDao(DatabaseBaseTest):
    
    def setUp(self):
        super().setUp()
        
        self.document_filter_expression_builder = DocumentFilterExpressionBuilder()
        self.event_filter_expression_builder = EventFilterExpressionBuilder()
        
        self.dao = DocumentEventRelationsDao(self.engine, self.document_filter_expression_builder, self.event_filter_expression_builder)
        
    def test_get_document_referencesevent_crossreferences(self):
        
        de_filter = DocumentEventReferenceFilter()
        de_filter.signature = "1.1"
        
        references = self.dao.fetch_doc_event_references(de_filter)

        self.assertEqual(2, len(references))
        self.assertEqual(2, len(references[4]))

        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()