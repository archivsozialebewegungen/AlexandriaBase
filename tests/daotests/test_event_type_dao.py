'''
Created on 11.10.2015

@author: michael
'''
import unittest

from alexandriabase.daos import EventTypeDao
from daotests.test_base import DatabaseBaseTest
from alexandriabase.domain import EventTypeIdentifier


class TestEverweisDao(DatabaseBaseTest):
    
    def setUp(self):
        super().setUp()
        self.dao = EventTypeDao(self.engine)
        
    def test_get_event_type_for_event_id(self):
        
        liste = self.dao.get_event_types_for_event_id(1940000001)
        self.assertEqual(2, len(liste))
        self.assertEqual('Kundgebung', liste[0].description)
        self.assertEqual('Aufstand, Revolution', liste[1].description)
        
    def test_join_event_type_to_event_id(self):
        event_type = self.dao.get_by_id(EventTypeIdentifier(7, 1))
        self.dao.join_event_type_to_event_id(1940000001, event_type)
        liste = self.dao.get_event_types_for_event_id(1940000001)
        self.assertEqual(3, len(liste))
        
    def test_join_event_type_to_event_id_again(self):
        event_type = self.dao.get_by_id(EventTypeIdentifier(1, 2))
        self.dao.join_event_type_to_event_id(1940000001, event_type)
        liste = self.dao.get_event_types_for_event_id(1940000001)
        self.assertEqual(2, len(liste))

    def test_unlink_event_type_from_event_id(self):
        event_type = self.dao.get_by_id(EventTypeIdentifier(1, 2))
        self.dao.unlink_event_type_from_event_id(1940000001, event_type)
        liste = self.dao.get_event_types_for_event_id(1940000001)
        self.assertEqual(1, len(liste))
        
    def test_fetching_tree(self):
        tree = self.dao.get_event_type_tree()
        self.assertEqual(tree.root_node.id, EventTypeIdentifier(0,0))
        self.assertEqual(14, len(tree.root_node.children))
        self.assertEqual(8, len(tree.root_node.children[0].children))

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()