'''
Created on 11.10.2015

@author: michael
'''
from datetime import date
import unittest

from alexandriabase.daos.basiccreatorprovider import BasicCreatorProvider
from alexandriabase.daos.creatordao import CreatorDao
from alexandriabase.daos.documentdao import DocumentDao, \
    DocumentFilterExpressionBuilder
from alexandriabase.daos.documenttypedao import DocumentTypeDao
from alexandriabase.daos.eventdao import EventDao
from alexandriabase.daos.eventtypedao import EventTypeDao
from alexandriabase.domain import Document, DocumentFilter
from daotests.test_base import DatabaseBaseTest
import os
from alex_test_utils import get_testfiles_dir
from alexandriabase.config import Config
from alexandriabase.daos.metadata import DOCUMENT_TABLE
from sqlalchemy.sql.operators import like_op
from sqlalchemy.sql.expression import or_
from alexandriabase.daos.relationsdao import DocumentEventRelationsDao


class TestDocumentDao(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        config_file = os.path.join(get_testfiles_dir(), "testconfig.xml")
        self.config = Config(config_file)
        self.creator_dao = CreatorDao(self.engine)
        self.references_dao = DocumentEventRelationsDao(self.engine)
        self.eventtype_dao = EventTypeDao(self.engine)
        self.doc_type_dao = DocumentTypeDao(self.engine)
        creator_provider = BasicCreatorProvider(self.creator_dao)
        self.ereignis_dao = EventDao(self.engine,
                               self.creator_dao,
                               self.references_dao,
                               self.eventtype_dao,
                               creator_provider)
        self.dao = DocumentDao(self.engine,
                               self.config,
                               self.creator_dao,
                               self.doc_type_dao,
                               creator_provider)
        self.document_filter_handler = DocumentFilterExpressionBuilder()

    def tearDown(self):
        super().tearDown()

    def test_hashing(self):

        doc1 = Document();
        doc2 = Document();
        doc1.description = None
        doc2.description = None
        test_map = {}
        test_map[doc1] = "eins"
        test_map[doc2] = "zwei"

        self.assertEqual(test_map[doc2], "zwei")

    def test_get_first_and_mapping(self):
        dokument = self.dao.get_first()
        self.assertTrue(dokument)
        self.assertEqual(dokument.id, 1)
        self.assertEqual(dokument.description, "Erstes Dokument")
        self.assertEqual(dokument.creation_date, date(2014, 12, 31))
        self.assertEqual(dokument.change_date, date(2015, 1, 13))
        self.assertEqual(dokument.condition, 'Guter Zustand')
        self.assertEqual(dokument.keywords, 'Suchwort')

    def test_get_by_id(self):
        dokument = self.dao.get_by_id(4)
        self.assertEqual(dokument.id, 4)

    def test_get_last(self):
        dokument = self.dao.get_last()
        self.assertEqual(dokument.id, 14)

    def test_get_next_with_wrap_around(self):
        dokument = self.dao.get_first()
        self.assertEqual(dokument.id, 1)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 4)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 8)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 11)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 12)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 13)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 14)
        dokument = self.dao.get_next(dokument)
        self.assertEqual(dokument.id, 1)

    def test_get_previous_with_wrap_around(self):
        dokument = self.dao.get_last()
        self.assertEqual(dokument.id, 14)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 13)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 12)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 11)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 8)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 4)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 1)
        dokument = self.dao.get_previous(dokument)
        self.assertEqual(dokument.id, 14)

    def test_get_nearest(self):
        document = self.dao.get_nearest(4)
        self.assertEqual(document.id, 4)
        document = self.dao.get_nearest(5)
        self.assertEqual(document.id, 8)
        document = self.dao.get_nearest(9)
        self.assertEqual(document.id, 11)
        filter_expression = self.dao.table.c.hauptnr > 4
        document = self.dao.get_nearest(4, filter_expression)
        self.assertEqual(document.id, 8)

    def test_get_on_empty_database_table(self):
        document = self.dao.get_first()
        while document:
            self.dao.delete(document.id)
            document = self.dao.get_first()
        self.assertFalse(self.dao.get_first())
        self.assertFalse(self.dao.get_last())


    def test_filtering_1(self):
        document_filter = DocumentFilter()
        document_filter.searchterms = ["weit"]
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_previous(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_last(filter_expression)
        self.assertEqual(document.id, 4)

    def test_filtering_2(self):
        document_filter = DocumentFilter()
        document_filter.searchterms = ["ritt", "weit"]
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(document.id, 8)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_previous(document, filter_expression)
        self.assertEqual(document.id, 8)
        document = self.dao.get_previous(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_last(filter_expression)
        self.assertEqual(document.id, 8)

    def test_filtering_3(self):
        document_filter = DocumentFilter()
        # Erster Term: 'Erstes', 'Drittes' 'Viertes'
        # Zweiter Term: 'Zweites', 'Drittes', 'Viertes'
        # Schnittmenge: 'Drittes', 'Viertes'
        document_filter.searchterms = ["r", "i"]
        document_filter.combine_searchterms_by_or = False 
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        documents = self.dao.find(filter_expression)
        self.assertEqual(2, len(documents))

    def test_filtering_4(self):
        '''
        Test that repeated expression generation yields the same result
        '''
        document_filter = DocumentFilter()
        document_filter.searchterms = ["weit"]
        filter_expression1 = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression1)
        self.assertEqual(document.id, 4)
        document_filter.searchterms = ["unsinn"]
        filter_expression2 = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression2)
        self.assertEqual(document, None)
        document_filter.searchterms = ["weit"]
        filter_expression3 = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression3)
        self.assertEqual(document.id, 4)

    def test_filtering_5(self):
        '''
        Test that case insensitive filtering works
        
        This test actually does not work because sqlite
        always searches case sensitive
        '''
        document_filter = DocumentFilter()
        document_filter.searchterms = ["RITT", "WEIT"]
        document_filter.case_sensitive = False
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(document.id, 8)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_previous(document, filter_expression)
        self.assertEqual(document.id, 8)
        document = self.dao.get_previous(document, filter_expression)
        self.assertEqual(document.id, 4)
        document = self.dao.get_last(filter_expression)
        self.assertEqual(document.id, 8)

    def testLocationFiltering(self):
        document_filter = DocumentFilter()
        document_filter.location = "1.1"
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_last(filter_expression)
        self.assertEqual(4, document.id)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(1, document.id)

    def testFileTypeFiltering(self):
        document_filter = DocumentFilter()
        document_filter.filetype = "txt"
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_first(filter_expression)
        self.assertEqual(4, document.id)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(11, document.id)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(12, document.id)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(4, document.id)

    def testCombinedFiltering(self):
        document_filter = DocumentFilter()
        document_filter.location = "1.1"
        document_filter.searchterms = ["rstes"]
        filter_expression = self.document_filter_handler.create_filter_expression(document_filter)
        document = self.dao.get_last(filter_expression)
        self.assertEqual(1, document.id)
        document = self.dao.get_next(document, filter_expression)
        self.assertEqual(1, document.id)

    def testUpdateDocument(self):
        document = self.dao.get_first();
        aenderung_old = document.change_date
        erfasser_old = document.erfasser
        document.description = "New description"
        document.condition = "New state"
        document.keywords = "New keywords"
        document.standort = "1.2.3.IV"
        document.document_type = self.doc_type_dao.get_by_id(17)

        self.dao.save(document)

        document = self.dao.get_first();
        self.assertTrue(document.change_date > aenderung_old)
        self.assertEqual(erfasser_old, document.erfasser)
        self.assertEqual(document.description, "New description")
        self.assertEqual(document.condition, "New state")
        self.assertEqual(document.keywords, "New keywords")

    def testDeleteDocument(self):
        document = self.dao.get_first()
        self.assertEqual(1, document.id)
        self.dao.delete(document.id)
        document = self.dao.get_first()
        self.assertEqual(4, document.id)

    def testSaveNewDocument(self):
        document = Document()
        document.description = "My description"
        document.keywords = "My keywords"
        document.condition = "My document state"
        document.erfasser = self.creator_dao.get_by_id(2)
        document.document_type = self.doc_type_dao.get_by_id(5)
        self.dao.save(document)

        document = self.dao.get_last()
        
        self.assertEqual(15, document.id)
        self.assertEqual("My description", document.description)
        self.assertEqual("My keywords", document.keywords)
        self.assertEqual("My document state", document.condition)
        self.assertEqual(3, document.erfasser.id)
        self.assertEqual("Flugblatt", document.document_type.description)
        self.assertTrue(document.change_date)
        self.assertTrue(document.creation_date)
        
    def test_get_statistics(self):
        
        statistics = self.dao.get_statistics()
        self.assertEqual(14, statistics.number_of_files)
        self.assertEqual(7, statistics.number_of_documents)
        self.assertEqual(6, len(statistics.number_of_files_by_type))
        self.assertEqual(1, statistics.number_of_files_by_type['pdf'])

    def test_find_all_entities(self):
        
        entities = self.dao.find(None, 1, 10)
        self.assertEqual(7, len(entities))
        
    def test_find_paginated_entities(self):
        
        entities = self.dao.find(None, 1, 3)
        self.assertEqual(3, len(entities))
        self.assertEqual(1, entities[0].id)
        self.assertEqual(4, entities[1].id)
        self.assertEqual(8, entities[2].id)
        entities = self.dao.find(None, 2, 3)
        self.assertEqual(3, len(entities))
        self.assertEqual(11, entities[0].id)
        self.assertEqual(12, entities[1].id)
        self.assertEqual(13, entities[2].id)
        
    def test_find_paginated_entities_with_filter(self):
        columns = DOCUMENT_TABLE.c
        where = or_(columns.beschreibung.contains("Zweites"),
                    columns.beschreibung.contains("Drittes"),
                    columns.beschreibung.contains("Viertes"),
                    columns.beschreibung.contains("Fünftes")) 
        entities = self.dao.find(where, 1, 2)
        self.assertEqual(2, len(entities))
        self.assertEqual(4, entities[0].id)
        self.assertEqual(8, entities[1].id)
        entities = self.dao.find(where, 2, 2)
        self.assertEqual(2, len(entities))
        self.assertEqual(11, entities[0].id)
        self.assertEqual(12, entities[1].id)

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
