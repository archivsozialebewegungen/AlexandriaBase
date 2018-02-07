'''
Created on 21.10.2015

@author: michael
'''
import unittest
from unittest.mock import MagicMock

from alexandriabase.domain import Document, Event
from alexandriabase.daos import EventDao, DocumentDao, DocumentEventRelationsDao
from alexandriabase.services import ReferenceService


class Test(unittest.TestCase):


    def setUp(self):
        self.event_dao = MagicMock(spec=EventDao)
        self.document_dao = MagicMock(spec=DocumentDao)
        self.references_dao = MagicMock(spec=DocumentEventRelationsDao)
        self.service = ReferenceService(self.event_dao, self.document_dao, self.references_dao)

    def testGetEventsReferencedByDocument(self):
                # Test setup
        document_stub = MagicMock(spec=Document)
        document_stub.id = 1
        self.references_dao.fetch_ereignis_ids_for_dokument_id = MagicMock(return_value=[2,3])

        event1_stub = MagicMock(spec=Event)
        event1_stub.id = 2
        event2_stub = MagicMock()
        event2_stub.id = 3
        values = {2: event1_stub, 3: event2_stub}
        def side_effect(arg):
            return values[arg]
        self.event_dao.get_by_id = MagicMock(side_effect=side_effect)
        # Execution
        result = self.service.get_events_referenced_by_document(document_stub)
        # Assertion
        self.references_dao.fetch_ereignis_ids_for_dokument_id.assert_called_once_with(1)
        self.assertEqual(len(result), 2)
        self.assertIn(event1_stub, result)
        self.assertIn(event2_stub, result)

    def testGetDocumentsReferencedByEvent(self):
                # Test setup
        event_stub = MagicMock(spec=Event)
        event_stub.id = 1
        self.references_dao.fetch_document_ids_for_event_id = MagicMock(return_value=[2,3])

        document1_stub = MagicMock(spec=Document)
        document1_stub.id = 2
        document2_stub = MagicMock()
        document2_stub.id = 3
        values = {2: document1_stub, 3: document2_stub}
        def side_effect(arg):
            return values[arg]
        self.document_dao.get_by_id = MagicMock(side_effect=side_effect)
        # Execution
        result = self.service.get_documents_referenced_by_event(event_stub)
        # Assertion
        self.references_dao.fetch_document_ids_for_event_id.assert_called_once_with(1)
        self.assertEqual(len(result), 2)
        self.assertIn(document1_stub, result)
        self.assertIn(document2_stub, result)
        
    def testLinkDocumentToEvent(self):
        event_stub = MagicMock(spec=Event)
        event_stub.id = 1

        document_stub = MagicMock(spec=Document)
        document_stub.id = 2
        
        self.service.link_document_to_event(document_stub, event_stub)

        self.references_dao.join_document_id_with_event_id.assert_called_once_with(2, 1)

    def testDeleteDocumentEventRelation(self):
        event_stub = MagicMock(spec=Event)
        event_stub.id = 1

        document_stub = MagicMock(spec=Document)
        document_stub.id = 2
        
        self.service.delete_document_event_relation(document_stub, event_stub)

        self.references_dao.delete_document_event_relation.assert_called_once_with(2, 1)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()