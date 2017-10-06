'''
Created on 18.10.2015

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys


class ReferenceService:
    '''
    Service for handling references to the main records.
    '''
    
    @inject
    def __init__(self,
                 event_dao: baseinjectorkeys.EVENT_DAO_KEY, 
                 document_dao: baseinjectorkeys.DOCUMENT_DAO_KEY, 
                 references_dao: baseinjectorkeys.RELATIONS_DAO_KEY):
        '''
        Used for injection.
        '''
        self.event_dao = event_dao
        self.document_dao = document_dao
        self.references_dao = references_dao
        
    def get_events_referenced_by_document(self, document):
        '''
        Returns the events that are related to a document.
        '''
        event_ids = self.references_dao.fetch_ereignis_ids_for_dokument_id(document.id)
        events = []
        for event_id in event_ids:
            events.append(self.event_dao.get_by_id(event_id))
        return events

    def get_documents_referenced_by_event(self, event):
        '''
        Returns the documents that are related to an event.
        '''
        document_ids = self.references_dao.fetch_document_ids_for_event_id(event.id)
        documents = []
        for document_id in document_ids:
            documents.append(self.document_dao.get_by_id(document_id))
        return documents

    def link_document_to_event(self, document, event):
        '''
        Creates a reference between a document and an event.
        '''
        self.references_dao.join_document_id_with_event_id(document.id, event.id)
    
    def delete_document_event_relation(self, document, event):
        '''
        Removes the reference between a document and an event.
        '''
        self.references_dao.delete_document_event_relation(document.id, event.id)
