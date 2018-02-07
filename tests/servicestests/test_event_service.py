'''
Created on 20.10.2015

@author: michael
'''
import unittest
from unittest.mock import MagicMock 

from alexandriabase.domain import AlexDateRange, Event, \
    alex_date_from_key, EventType, EventTypeIdentifier
from alexandriabase.daos import EventFilterExpressionBuilder,\
    EventCrossreferencesDao, EventTypeDao, EventDao
from alexandriabase.services import EventService


class Test(unittest.TestCase):


    def setUp(self):
        self.event_dao = MagicMock(spec=EventDao)
        self.filter_expression_builder = MagicMock(spec=EventFilterExpressionBuilder)
        self.event_crossreferences_dao = MagicMock(spec=EventCrossreferencesDao)
        self.event_type_dao = MagicMock(spec=EventTypeDao)
        self.event_service = EventService(self.event_dao, 
                                          self.filter_expression_builder, 
                                          self.event_crossreferences_dao,
                                          self.event_type_dao)

    def test_get_nearest(self):
        date = alex_date_from_key(2015010100)
        self.event_service.get_nearest(date, None)
        self.event_dao.get_nearest.assert_called_once_with(date, None)

    def test_create_new(self):
        date_range = AlexDateRange(alex_date_from_key(2015010100), None)
        event = self.event_service.create_new(date_range)
        self.assertIsInstance(event, Event)
        self.assertEqual(event.daterange, date_range)
        
    def test_delete(self):
        event = Event(4711)
        self.event_service.delete(event)
        self.event_dao.delete.assert_called_once_with(4711)

    def testGetEventsByDate(self):
        alex_date = alex_date_from_key(2015010100)
        self.event_service.get_events_for_date(alex_date)
        self.event_dao.get_events_for_date.assert_called_with(alex_date)
        
    def testGetCrossReferences(self):
        # Test setup
        event1_stub = MagicMock()
        event1_stub.id = 1
        self.event_crossreferences_dao.get_cross_references = MagicMock(return_value=[2,3])

        event2_stub = MagicMock()
        event2_stub.id = 2
        event3_stub = MagicMock()
        event3_stub.id = 3
        values = {2: event2_stub, 3: event3_stub}
        def side_effect(arg):
            return values[arg]
        self.event_dao.get_by_id = MagicMock(side_effect=side_effect)
        # Execution
        result = self.event_service.get_cross_references(event1_stub)
        # Assertion
        self.event_crossreferences_dao.get_cross_references.assert_called_once_with(1)
        self.assertEqual(len(result), 2)
        self.assertIn(event2_stub, result)
        self.assertIn(event3_stub, result)
        
    def testGetCrossReferencesWithNone(self):
        result = self.event_service.get_cross_references(None)
        # Assertion
        self.assertEqual(len(result), 0)

    def testAddCrossreference(self):
        event1_stub = MagicMock()
        event1_stub.id = 1
        event2_stub = MagicMock()
        event2_stub.id = 2
        self.event_service.add_cross_reference(event1_stub, event2_stub)
        self.event_crossreferences_dao.add_cross_reference.assert_called_once_with(1, 2)

    def testRemoveCrossreference(self):
        event1_stub = MagicMock()
        event1_stub.id = 1
        event2_stub = MagicMock()
        event2_stub.id = 2
        self.event_service.remove_cross_reference(event1_stub, event2_stub)
        self.event_crossreferences_dao.remove_cross_reference.assert_called_once_with(1, 2)
        
    def test_get_event_types(self):
        
        event = Event(1940000001)
        event_type = EventType(EventTypeIdentifier(5, 1), "Test")
        self.event_type_dao.get_event_types_for_event_id.return_value = [event_type]
        result = self.event_service.get_event_types(event)
        self.assertEqual(1, len(result))
        self.assertEqual(event_type, result[0])
        self.event_type_dao.get_event_types_for_event_id.assert_called_once_with(1940000001)
        
    def test_add_event_type(self):
        
        event = Event(1940000001)
        event_type = EventType(EventTypeIdentifier(1, 5), "Test")
        self.event_service.add_event_type(event, event_type)
        
        self.event_type_dao.join_event_type_to_event_id.assert_called_once_with(1940000001, event_type)

    def test_remove_event_type(self):
        
        event = Event(1940000001)
        event_type = EventType(EventTypeIdentifier(1, 5), "Test")
        self.event_service.remove_event_type(event, event_type)
        
        self.event_type_dao.unlink_event_type_from_event_id.assert_called_once_with(1940000001, event_type)

    def test_get_event_type_tree(self):
        
        self.event_type_dao.find_all.return_value = [EventType(EventTypeIdentifier(1,0), "one_zero"),
                                                     EventType(EventTypeIdentifier(1,1), "one_one"),
                                                     EventType(EventTypeIdentifier(2,0), "two_zero"),
                                                     EventType(EventTypeIdentifier(2,1), "two_one")
                                                     ]
        tree = self.event_service.get_event_type_tree()
        self.assertFalse(tree is None)
        self.assertFalse(tree.root_node is None)
        self.assertEqual(2, len(tree.root_node.children))
        self.assertEqual("one_zero", tree.root_node.children[0].entity.description)
        self.assertEqual("two_zero", tree.root_node.children[1].entity.description)
        self.assertEqual(1, len(tree.root_node.children[0].children))
        self.assertEqual(1, len(tree.root_node.children[1].children))
        self.assertEqual("one_one", tree.root_node.children[0].children[0].entity.description)
        self.assertEqual("two_one", tree.root_node.children[1].children[0].entity.description)
    
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()