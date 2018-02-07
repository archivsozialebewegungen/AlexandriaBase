'''
Created on 11.10.2015

@author: michael
'''
import unittest

from alexandriabase.daos import EventCrossreferencesDao
from daotests.test_base import DatabaseBaseTest


class TestEventCrossreferencesDao(DatabaseBaseTest):
    
    def setUp(self):
        super().setUp()
        self.dao = EventCrossreferencesDao(self.engine)
        
    def test_get_event_crossreferences(self):
        
        liste = self.dao.get_cross_references(1940000001)
        self.assertEqual(2, len(liste))
        self.assertIn(1950000001, liste)
        self.assertIn(1960013001, liste)
        
    def test_add_event_crossreference(self):
        event_id1 = 1940000001
        event_id2 = 1961050101
        
        # Before
        liste1 = self.dao.get_cross_references(event_id1)
        self.assertNotIn(event_id2, liste1)
        liste2 = self.dao.get_cross_references(event_id2)
        self.assertNotIn(event_id1, liste2)
        
        self.dao.add_cross_reference(event_id1, event_id2)
        
        #After
        liste1 = self.dao.get_cross_references(event_id1)
        self.assertIn(event_id2, liste1)
        liste2 = self.dao.get_cross_references(event_id2)
        self.assertIn(event_id1, liste2)
        
    def test_remove_event_crossreference(self):
        event_id1 = 1940000001
        event_id2 = 1950000001
        
        # Before
        liste1 = self.dao.get_cross_references(event_id1)
        self.assertIn(event_id2, liste1)
        liste2 = self.dao.get_cross_references(event_id2)
        self.assertIn(event_id1, liste2)
        
        self.dao.remove_cross_reference(event_id1, event_id2)
        
        # After
        liste1 = self.dao.get_cross_references(event_id1)
        self.assertNotIn(event_id2, liste1)
        liste2 = self.dao.get_cross_references(event_id2)
        self.assertNotIn(event_id1, liste2)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()