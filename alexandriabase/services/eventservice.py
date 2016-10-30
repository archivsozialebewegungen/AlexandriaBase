'''
Created on 18.10.2015

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys
from alexandriabase.domain import Event, Tree, EventType, EventTypeIdentifier
from alexandriabase.services.baseservice import BaseRecordService


class EventService(BaseRecordService):
    '''
    Service for event handling. Most of the calls are just
    passed through to the daos.
    '''

    @inject(ereignis_dao=baseinjectorkeys.EreignisDaoKey,
            filter_expression_builder=baseinjectorkeys.EVENT_FILTER_EXPRESSION_BUILDER_KEY,
            event_crossreferences_dao=baseinjectorkeys.EventCrossreferencesDaoKey,
            event_type_dao=baseinjectorkeys.EventTypeDaoKey)
    def __init__(self,
                 ereignis_dao,
                 filter_expression_builder,
                 event_crossreferences_dao,
                 event_type_dao):
        BaseRecordService.__init__(self, ereignis_dao, filter_expression_builder)
        self.event_crossreferences_dao = event_crossreferences_dao
        self.event_type_dao = event_type_dao

    def get_nearest(self, event_date, filter_expression):
        return self.dao.get_nearest(event_date, filter_expression)

    def get_events_for_date(self, alex_date):
        '''
        Returns all events that have the given start date
        '''
        return self.dao.get_events_for_date(alex_date)

    def get_cross_references(self, event):
        '''
        Returns all events that are crossreferenced to the given event.
        '''
        if event is None:
            return []
        crossreference_ids = self.event_crossreferences_dao.get_cross_references(event.id)
        events = []
        for crossreference_id in crossreference_ids:
            events.append(self.dao.get_by_id(crossreference_id))
        return events

    def remove_cross_reference(self, event1, event2):
        '''
        Removes the crossreference between the given two events.
        '''
        self.event_crossreferences_dao.remove_cross_reference(event1.id, event2.id)

    def add_cross_reference(self, event1, event2):
        '''
        Crossreferences the two given events.
        '''
        self.event_crossreferences_dao.add_cross_reference(event1.id, event2.id)

    def create_new(self, date_range):
        '''
        Creates a new event object for the given date range.
        '''
        # pylint: disable=no-self-use
        event = Event()
        event.daterange = date_range
        return event

    def delete(self, event):
        self.dao.delete(event.id)
        
    def get_event_types(self, event):
        '''
        Fetches the event types registered for the given event.
        '''
        return self.event_type_dao.get_event_types_for_event_id(event.id)
    
    def add_event_type(self, event, event_type):
        '''
        Registers a new event type for the given event.
        '''
        self.event_type_dao.join_event_type_to_event_id(event.id, event_type)
    
    def remove_event_type(self, event, event_type):
        '''
        Removes an event type from the list of event
        types registered with the given event.
        '''
        self.event_type_dao.unlink_event_type_from_event_id(event.id, event_type)
        
    def get_event_type_tree(self):
        '''
        Returns all event types wrapped into a tree object.
        '''
        entities = self.event_type_dao.find_all()
        entities.append(
            EventType(EventTypeIdentifier(0, 0), 
                      _("Event types")))

        return Tree(entities)
