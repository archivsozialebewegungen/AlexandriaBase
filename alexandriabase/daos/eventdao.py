'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, and_, insert, update
from sqlalchemy.sql.functions import func

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import GenericFilterExpressionBuilder, EntityDao
from alexandriabase.daos.metadata import EVENT_TABLE
from alexandriabase.domain import AlexDateRange, Event, alex_date_from_key


class EventFilterExpressionBuilder(GenericFilterExpressionBuilder):
    '''
    Converts a EventFilterObject into a sql alchemy expression usable
    for queries.
    '''

    def __init__(self):
        super().__init__()
        self.table = EVENT_TABLE
        self.textcolumn = self.table.c.ereignis
        
    def _create_expressions(self, filter_object):
        super()._create_expressions(filter_object)
        self._append_expression(self._build_earliest_date_expression(filter_object))
        self._append_expression(self._build_latest_date_expression(filter_object))
        self._append_expression(self._build_local_only_expression(filter_object))
        self._append_expression(self._build_unverified_expression(filter_object))

    def _build_earliest_date_expression(self, filter_object):
        '''
        Adds expression to filter for earliest date.
        '''
        if filter_object.earliest_date is None:
            return None
        return self.table.c.ereignis_id >= filter_object.earliest_date.as_key(0)

    def _build_latest_date_expression(self, filter_object):
        '''
        Adds expression to filter for latest date.
        '''
        if filter_object.latest_date is None:
            return None
        return self.table.c.ereignis_id <= filter_object.latest_date.as_key(99)

    def _build_local_only_expression(self, filter_object):
        '''
        Adds expression to filter for local events.
        '''

        if not filter_object.local_only:
            return None
        return self.table.c.ort_id == 1

    def _build_unverified_expression(self, filter_object):
        '''
        Adds expression to filter for unverified events.
        '''
        if not filter_object.unverified_only:
            return None
        return self.table.c.status_id == 0

class EventDao(EntityDao):
    '''
    Persistance dao for events.
    '''

    @inject(db_engine=baseinjectorkeys.DBEngineKey,
            creator_dao=baseinjectorkeys.CREATOR_DAO_KEY,
            references_dao=baseinjectorkeys.RelationsDaoKey,
            eventtype_dao=baseinjectorkeys.EventTypeDaoKey,
            creator_provider=baseinjectorkeys.CreatorProvider)
    def __init__(self,
                 db_engine,
                 creator_dao,
                 references_dao,
                 eventtype_dao,
                 creator_provider):
        '''
        Constructor with a lot of dependency injection.
        '''
        # pylint: disable=too-many-arguments
        super().__init__(db_engine, EVENT_TABLE)
        self.creator_dao = creator_dao
        self.references_dao = references_dao
        self.eventtype_dao = eventtype_dao
        self.creator_provider = creator_provider

    def get_nearest(self, alex_date, filter_expression=None):
        ''' Get the entity matching the date, or, if not existing,
        the next entity after this date. If this does not provide
        an entity, get the last entity.'''
        min_id = alex_date.as_key(1)
        return super().get_nearest(min_id, filter_expression)

    def _update(self, event):
        '''
        Update an existing event. Decides, it the id has to be changed
        '''
        # pylint: disable=protected-access
        date_from_id = alex_date_from_key(event.id)
        date_from_range = event.daterange.start_date
        if date_from_id != date_from_range:
            # Normally you should never change the id, so the id
            # property is protected. But in this case here, due to
            # bad database design, it is necessary to change the id
            # of a record, so we change the private property
            event._id = self._run_date_change(event, date_from_range)
        self._normal_update(event)
        return event

    def _insert(self, ereignis):
        '''
        Inserts a new event into the database.
        '''
        # pylint: disable=protected-access
        start_date = ereignis.daterange.start_date
        sequence_no = self._get_next_free_sequence_id(start_date)
        # Normally you shouldn't set the id, but the
        # database is not designed very well, so we set
        # the id manually
        ereignis._id = start_date.as_key(sequence_no)
        end_date = ereignis.daterange.end_date
        if end_date:
            end_date = end_date.as_key(0)
        ereignis.erfasser = self.creator_provider.creator
        insert_statement = insert(self.table).\
            values(ereignis_id=ereignis.id,
                   ereignis=ereignis.description,
                   ende=end_date,
                   status_id=ereignis.status_id,
                   ort_id=ereignis.location_id,
                   erfasser_id=ereignis.erfasser.id,
                   aufnahme=func.now(),
                   aenderung=func.now())
        self._get_connection().execute(insert_statement)
        return ereignis

    def _run_date_change(self, event, new_date):
        '''
        Evil method to change the id of the event, because
        the id has also a semantic meaning.
        '''
        sequence_id = self._get_next_free_sequence_id(new_date)
        new_id = new_date.as_key(sequence_id)
        for foreign_key in self.foreign_keys:
            key_words = {}
            key_words[foreign_key.name] = new_id
            update_statement = update(foreign_key.table)\
                .values(**key_words)\
                .where(foreign_key == event.id)
            self.connection.execute(update_statement)
        update_statement = update(self.table).values(ereignis_id=new_id).\
        where(self.table.c.ereignis_id == event.id)  
        self.connection.execute(update_statement)
        return new_id

    def _get_next_free_sequence_id(self, alex_date):
        '''
        Searches for the next sequence key for a certain date.
        This is some real crappy database design where you
        just may have up to 99 events for a date.
        '''
        min_key = alex_date.as_key(0)
        max_key = min_key + 99
        function = func.max(self.table.c.ereignis_id)  
        max_existing_query = select([function]).where(
            and_(self.table.c.ereignis_id > min_key,  
                 self.table.c.ereignis_id <= max_key))  
        result = self.connection.execute(max_existing_query)
        row = result.fetchone()
        if not row[0]:
            return 1
        max_existing_date = AlexDateRange(row[0], None)
        return max_existing_date.sequence_number + 1

    def _normal_update(self, ereignis):
        '''
        Update the general fields, but not the id.
        '''
        update_statement = update(self.table).\
        values(ereignis=ereignis.description,
               ort_id=ereignis.location_id,
               status_id=ereignis.status_id).\
            where(self.table.c.ereignis_id == ereignis.id)  
        self.connection.execute(update_statement)

    def _row_to_entity(self, row):
        '''
        Maps database row to event object.
        '''
        event = Event(row[self.table.c.ereignis_id])  
        event.key = row[self.table.c.ereignis_id]  
        event.description = row[self.table.c.ereignis]  
        event.daterange = AlexDateRange(row[self.table.c.ereignis_id],  
                                        row[self.table.c.ende])  
        event.status_id = row[self.table.c.status_id]  
        event.erfasser = self.creator_dao.get_by_id(row[self.table.c.erfasser_id])  
        event.creation_date = row[self.table.c.aufnahme]  
        event.change_date = row[self.table.c.aenderung]  
        event.location_id = row[self.table.c.ort_id]  

        return event

    def get_events_for_date(self, alex_date):
        '''
        Select all events for a certain date
        '''
        min_id = alex_date.as_key(0)
        max_id = alex_date.as_key(99)
        query = select([self.table]).where(
            and_(self.table.c.ereignis_id > min_id,  
                 self.table.c.ereignis_id < max_id))  
        result = self._get_connection().execute(query)
        events = []
        for row in result:
            events.append(self._row_to_entity(row))
        return events
