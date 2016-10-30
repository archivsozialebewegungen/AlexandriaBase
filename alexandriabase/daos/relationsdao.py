'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, insert, and_, delete, update
from sqlalchemy.sql.functions import func

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import GenericDao, combine_expressions
from alexandriabase.daos.metadata import DOCUMENT_EVENT_REFERENCE_TABLE, DOCUMENT_TABLE

class DocumentEventRelationsDao(GenericDao):
    '''
    Handles all kinds of relations
    '''
    
    @inject(db_engine=baseinjectorkeys.DBEngineKey)
    def __init__(self, db_engine):
        super().__init__(db_engine)
        self.deref_table = DOCUMENT_EVENT_REFERENCE_TABLE
        self.doc_table = DOCUMENT_TABLE
        
    # TODO: clean up the references and use pages instead of file ids
    def fetch_doc_file_ids_for_event_id(self, event_id):
        '''
        Theoretically it is possible to reference an event to
        a single document file of a document. So you won't get
        the document id, but the document file id when querying.
        This method should probably not be used in any context.
        '''
        query = select([self.deref_table.c.laufnr]).where(
            self.deref_table.c.ereignis_id == event_id)  
        result = self._get_connection().execute(query)
        file_ids = []
        for row in result.fetchall():
            file_ids.append(row[self.deref_table.c.laufnr])  
        result.close()
        return file_ids
    
    def fetch_document_ids_for_event_id(self, ereignis_id):
        '''
        Fetches the document ids for an event id. Since the join table
        does not link document ids but document file ids the query is
        complicated.
        '''
        subquery = select([self.deref_table.c.laufnr]).where(
            self.deref_table.c.ereignis_id == ereignis_id)  
        query = select([self.doc_table.c.hauptnr]).where(
            self.doc_table.c.laufnr.in_(subquery)).distinct().order_by(
                self.doc_table.c.hauptnr)  
        result = self._get_connection().execute(query)
        dokument_ids = []
        for row in result.fetchall():
            dokument_ids.append(row[self.doc_table.c.hauptnr])  
        result.close()
        return dokument_ids
    
    def join_document_id_with_event_id(self, document_id, event_id):
        '''
        Adds the document and event ids into the join table
        '''
        if document_id in self.fetch_document_ids_for_event_id(event_id):
            # already joined
            return 
        insert_statement = insert(self.deref_table).\
            values(ereignis_id=event_id,
                   laufnr=document_id)
        self._get_connection().execute(insert_statement)
        
    # TODO: This method does not work correctly, when a document file
    #       is linked that is not the first document file for the document.
    def delete_document_event_relation(self, document_id, event_id):
        '''
        Unlinks a document from an event.
        '''
        delete_statement = delete(self.deref_table).where(
            and_(self.deref_table.c.ereignis_id == event_id,  
                 self.deref_table.c.laufnr == document_id))  
        self._get_connection().execute(delete_statement)

    def fetch_doc_event_references(self, start_date=None, end_date=None, location=None):

        join = self.doc_table.outerjoin(
            self.deref_table,
            self.doc_table.c.hauptnr == self.deref_table.c.laufnr)        
        query = select([self.doc_table.c.hauptnr, self.deref_table.c.ereignis_id]).distinct().select_from(join)
        where_clauses = []
        if end_date is not None or start_date is not None:
            where_clauses.append(self.deref_table.c.ereignis_id != None)
        if start_date is not None:
            where_clauses.append(self.deref_table.c.ereignis_id >= start_date.as_key(0))
        if end_date is not None:
            where_clauses.append(self.deref_table.c.ereignis_id < end_date.as_key(0)+100)
        if location is not None:
            where_clauses.append(self.doc_table.c.standort.ilike("%s%%" % location))
        if len(where_clauses) > 0:
            query = query.where(combine_expressions(where_clauses, and_))

        references = {}
        for row in self._get_connection().execute(query):
            document_id = row[self.doc_table.c.hauptnr]
            event_id = row[self.deref_table.c.ereignis_id]
            if not document_id in references:
                references[document_id] = []
            if event_id is not None:
                references[document_id].append(event_id)
            
        return references
    
    def fetch_ereignis_ids_for_dokument_id(self, dokument_id):
        '''
        Does what the method name says.
        '''
        subquery = select([self.doc_table.c.laufnr]).\
            where(self.doc_table.c.hauptnr == dokument_id)  
        query = select([self.deref_table.c.ereignis_id]).\
            where(self.deref_table.c.laufnr.in_(subquery)).\
            distinct().\
            order_by(self.deref_table.c.ereignis_id)  
        result = self._get_connection().execute(query)
        ereignis_ids = []
        for row in result.fetchall():
            ereignis_ids.append(row[self.deref_table.c.ereignis_id])  
        result.close()
        return ereignis_ids
