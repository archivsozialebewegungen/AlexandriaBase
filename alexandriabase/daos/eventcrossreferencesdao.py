'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, insert, delete, and_

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import GenericDao
from alexandriabase.daos.metadata import EVENT_CROSS_REFERENCES_TABLE


class EventCrossreferencesDao(GenericDao):
    '''
    Handles the crossreferences between events.
    '''
    
    @inject(db_engine=baseinjectorkeys.DBEngineKey)
    def __init__(self, db_engine):
        super().__init__(db_engine)
        self.table = EVENT_CROSS_REFERENCES_TABLE

    def get_cross_references(self, event_id):
        '''
        Gets the event ids crossreferenced by the event given by the event_id parameter
        '''
        query = select([self.table.c.id2]).\
            where(self.table.c.id1 == event_id)
        result = self._get_connection().execute(query)
        event_ids = []
        for row in result.fetchall():
            event_ids.append(row[self.table.c.id2])
        return event_ids
    
    def add_cross_reference(self, event_id1, event_id2):
        '''
        Adds a cross reference between to events given by the parameter ids.
        '''
        self.transactional(self._add_cross_reference, event_id1, event_id2)
        
    def _add_cross_reference(self, event_id1, event_id2):
        '''
        The actual working method that is wrapped in a transaction by the
        public method.
        '''
        insert_statement = insert(EVENT_CROSS_REFERENCES_TABLE).values(
            id1=event_id1,
            id2=event_id2)
        self.connection.execute(insert_statement)
        insert_statement = insert(EVENT_CROSS_REFERENCES_TABLE).values(
            id1=event_id2,
            id2=event_id1)
        self.connection.execute(insert_statement)
    
    def remove_cross_reference(self, event_id1, event_id2):
        '''
        Transactional wrapper around removing a cross reference.
        '''
        self.transactional(self._remove_cross_reference, event_id1, event_id2)
        
    def _remove_cross_reference(self, event_id1, event_id2):
        '''
        Actual working method to remove a cross reference.
        '''
        delete_statement = delete(EVENT_CROSS_REFERENCES_TABLE).where(
            and_(self.table.c.id1 == event_id1,
                 self.table.c.id2 == event_id2))
        self.connection.execute(delete_statement)
        delete_statement = delete(self.table).where(
            and_(self.table.c.id1 == event_id2,
                 self.table.c.id2 == event_id1))
        self.connection.execute(delete_statement)
