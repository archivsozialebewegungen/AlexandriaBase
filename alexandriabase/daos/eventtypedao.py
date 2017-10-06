'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, insert, and_, delete

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import GenericDao
from alexandriabase.daos.metadata import EVENTTYPE_TABLE, EVENT_EVENTTYPE_REFERENCE_TABLE
from alexandriabase.domain import EventType, EventTypeIdentifier, Tree


class EventTypeDao(GenericDao):
    '''
    Dao for event types.
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        super().__init__(db_engine)
        self.table = EVENTTYPE_TABLE
        self.ref_table = EVENT_EVENTTYPE_REFERENCE_TABLE
        
    def get_by_id(self, event_type_id):
        '''
        Gets the event type from the cache. Loads the cache, if it
        was not filled.
        '''
        query = select([self.table]).where(
            and_(self.table.c.haupt == event_type_id.hauptid,
                 self.table.c.unter == event_type_id.unterid))
        row = self._get_exactly_one_row(query)
        return self._row_to_entity(row)
        
    def find_all(self):
        '''
        Fetches all event types.
        '''
        query = select([self.table])
        result = self._get_connection().execute(query)
        types = []
        for row in result.fetchall():
            types.append(self._row_to_entity(row))
        result.close()
        return types
    
    def get_event_type_tree(self):
        '''
        Fetches all event types and returns them as tree.
        '''
        entities = self.find_all()
        entities.append(EventType(EventTypeIdentifier(0, 0), _("Event types")))
        return Tree(entities)
            
    def get_event_types_for_event_id(self, ereignis_id):
        '''
        Fetches the event types for a certain event
        '''
        query = select([self.ref_table]).\
            where(
                self.ref_table.c.ereignis_id == ereignis_id
            ).order_by(
                self.ref_table.c.hauptid,
                self.ref_table.c.unterid
            )
        result = self._get_connection().execute(query)
        typelist = []
        for row in result.fetchall():
            typelist.append(
                self.get_by_id(
                    EventTypeIdentifier(
                        row[self.ref_table.c.hauptid],
                        row[self.ref_table.c.unterid])
                )
            )
        result.close()
        return typelist

    def join_event_type_to_event_id(self, event_id, event_type):
        '''
        Adds an event type to the given event.
        '''
        already_joined = self.get_event_types_for_event_id(event_id)
        if event_type in already_joined:
            return
        query = insert(self.ref_table).values(ereignis_id=event_id,
                                              hauptid=event_type.id.hauptid,
                                              unterid=event_type.id.unterid)
        self.connection.execute(query)
        
    def unlink_event_type_from_event_id(self, event_id, event_type):
        '''
        Removes an event type from the given event
        '''
        query = delete(self.ref_table).where(
            and_(self.ref_table.c.ereignis_id == event_id,
                 self.ref_table.c.hauptid == event_type.id.hauptid,
                 self.ref_table.c.unterid == event_type.id.unterid))
        self.connection.execute(query)

    def _row_to_entity(self, row):
        event_type_id = EventTypeIdentifier(row[self.table.c.haupt], row[self.table.c.unter])
        return EventType(event_type_id, row[self.table.c.beschreibung])
    
