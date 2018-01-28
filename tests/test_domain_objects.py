import unittest

from alexandriabase.base_exceptions import DataError
from alexandriabase.domain import InvalidChildException, InvalidDateException, AlexDate, \
    AlexDateRange, Creator, DocumentType, Event, DocumentFileInfo, Document, \
    EventType, EventTypeIdentifier, Tree, Node,\
    NoSuchNodeException
import pytest
import io
import logging


class AlexDateTests(unittest.TestCase):
    
    def test_invalid_date(self):
        exception_raised = False
        try:
            AlexDate(None)
        except InvalidDateException:
            exception_raised = True
        self.assertTrue(exception_raised)
        
class AlexDateRangeTests(unittest.TestCase):
    
    def test_key_generation(self):
        date_range = AlexDateRange(1970010155, 1970020100)
        self.assertEqual(date_range.get_key(), 1970010155)
        
    def test_initialization_from_dates(self):
        start = AlexDate(1970, 1, 1)
        end = AlexDate(1970, 2, 1)
        date_range = AlexDateRange(start, end)
        self.assertEqual("1. " + _("January") + " 1970 - 1. " + _("February") + " 1970", "%s" % date_range)
        
    def test_equality_I(self):
        date_range1 = AlexDateRange(1970010155, 1970020100)
        date_range2 = AlexDateRange(1970010155, 1970020100)
        self.assertEqual(date_range1, date_range2)

    def test_equality_II(self):
        date_range1 = AlexDateRange(1970010155, None)
        date_range2 = AlexDateRange(1970010155, None)
        self.assertEqual(date_range1, date_range2)

    def test_equality_III(self):
        date_range1 = AlexDateRange(1970010155, None)
        date_range2 = AlexDateRange(1970010155, 1970020100)
        self.assertNotEqual(date_range1, date_range2)

    def test_equality_IV(self):
        date_range1 = AlexDateRange(1970010155, 1970020100)
        date_range2 = AlexDateRange(1970010155, None)
        self.assertNotEqual(date_range1, date_range2)

    def test_equality_V(self):
        date_range = AlexDateRange(1970010155, 1970020100)
        self.assertNotEqual(date_range, None)
        self.assertNotEqual(None, date_range)
        
class CreatorTests(unittest.TestCase):
    
    def test_string_generation(self):
        
        creator = Creator(815)
        creator.name = "Jack the Ripper"
        self.assertEqual("%s" % creator, "Jack the Ripper")
        
class DocumentTypeTests(unittest.TestCase):
    
    def test_string_generation(self):
        
        document_type = DocumentType(4711)
        document_type.description = "Stundenbuch"
        self.assertEqual("%s" % document_type, "Stundenbuch")
        
class EventTests(unittest.TestCase):
    
    def test_string_generation(self):
        
        event = Event(1970040155)
        event.daterange = AlexDateRange(1970040155, 1970090100)
        event.description = "My event"
        self.assertEqual("%s" % event, "1. April 1970 - 1. September 1970: My event")
        
    def test_equality(self):
        event1 = Event(1970010155)
        event1.daterange = AlexDateRange(1970010155, 1970020100)
        event1.description = "My event"
        event2 = Event(1970010155)
        event2.daterange = AlexDateRange(1970010155, 1970020100)
        event2.description = "My event"
        self.assertEqual(event1, event2)

class DocumentFileInfoTests(unittest.TestCase):
    
    def test_filename_generation(self):
        
        info = DocumentFileInfo(4711)
        info.filetype = "txt"
        self.assertEqual(info.get_file_name(), "00004711.txt")

    def test_string_generation(self):
        
        info = DocumentFileInfo(4711)
        info.filetype = "txt"
        self.assertEqual("%s" % info , "00004711.txt")

    def test_string_generation_new_info(self):
        
        info = DocumentFileInfo()
        info.filetype = "txt"
        self.assertEqual("%s" % info , "New document file info")

class DocumentTests(unittest.TestCase):
    
    def test_string_generation(self):
        
        document = Document(4711)
        document.description = "My document"
        self.assertEqual("%s" % document, "4711: My document")
        
    def test_string_generation_new_document(self):
        
        document = Document()
        self.assertEqual("%s" % document, _('New document'))

    def test_hashable_with_id(self):
        
        dictionary = {}
        document = Document(4711)
        exception_raised = False
        try:
            dictionary[document] = "bla"
        except TypeError:
            exception_raised = True
        self.assertFalse(exception_raised)
        
    def test_hashable_without_id(self):
        
        dictionary = {}
        document = Document()
        exception_raised = False
        try:
            dictionary[document] = "bla"
        except TypeError:
            exception_raised = True
        self.assertFalse(exception_raised)

class EventTypeIdentifierTests(unittest.TestCase):
    
    
    def test_equals_with_none(self):
        
        self.assertFalse(EventTypeIdentifier(1, 2) == None)
                         
    def test_greater_or_equals(self):
        
        self.assertTrue(EventTypeIdentifier(1,2) >= EventTypeIdentifier(1,2))
        self.assertTrue(EventTypeIdentifier(2,2) >= EventTypeIdentifier(1,7))
        self.assertTrue(EventTypeIdentifier(1,1) >= EventTypeIdentifier(1,1))
        self.assertFalse(EventTypeIdentifier(1,1) >= EventTypeIdentifier(1,2))
        self.assertFalse(EventTypeIdentifier(1,1) >= EventTypeIdentifier(2,1))

    def test_less_or_equals(self):
        
        self.assertTrue(EventTypeIdentifier(1,2) <= EventTypeIdentifier(1,2))
        self.assertTrue(EventTypeIdentifier(1,6) <= EventTypeIdentifier(1,7))
        self.assertTrue(EventTypeIdentifier(1,7) <= EventTypeIdentifier(2,1))
        self.assertFalse(EventTypeIdentifier(1,1) <= EventTypeIdentifier(1,0))
        self.assertFalse(EventTypeIdentifier(3,1) <= EventTypeIdentifier(2,7))

class EventTypeTests(unittest.TestCase):
    
    def test_equals(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 2), "Test2")
        self.assertEqual(event_type1, event_type2)

    def test_not_equals(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 3), "Test")
        self.assertNotEqual(event_type1, event_type2)

    def test_compare_to_none(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        self.assertNotEqual(event_type1, None)
        
    def test_less_than_1(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 3), "Test2")
        self.assertTrue(event_type1 < event_type2)

    def test_less_than_2(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 7), "Test")
        event_type2 = EventType(EventTypeIdentifier(2, 1), "Test2")
        self.assertTrue(event_type1 < event_type2)

    def test_greater_than_1(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 3), "Test2")
        self.assertTrue(event_type2 > event_type1)

    def test_greater_than_2(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 7), "Test")
        event_type2 = EventType(EventTypeIdentifier(2, 1), "Test2")
        self.assertTrue(event_type2 > event_type1)

    def test_less_or_equal_than_1(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 7), "Test")
        event_type2 = EventType(EventTypeIdentifier(2, 1), "Test2")
        self.assertTrue(event_type1 <= event_type2)

    def test_less_or_equal_than_2(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 7), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 7), "Test2")
        self.assertTrue(event_type1 <= event_type2)

    def test_greater_or_equal_than_1(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 2), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 3), "Test2")
        self.assertTrue(event_type2 >= event_type1)

    def test_greater_or_equal_than_2(self):
        
        event_type1 = EventType(EventTypeIdentifier(1, 7), "Test")
        event_type2 = EventType(EventTypeIdentifier(1, 7), "Test2")
        self.assertTrue(event_type2 >= event_type1)

    def test_string_representation(self):

        event_type = EventType(EventTypeIdentifier(1, 2), "My event type")
        self.assertEqual("My event type", "%s" % event_type)

class TreeBuildingTest(unittest.TestCase):
    
    def setUp(self):

        class Entity:
            
            def __init__(self, id, parent_id):
                self.id = id
                self.parent_id = parent_id
                
            def __lt__(self, other):
                return self.id < other.id
            
            def __str__(self):
                
                return "String representation (%d)" % self.id

        # 1 - 2
        #   - 3
        #       - 5
        #       - 6
        #   - 4
        #       - 7
        self.entities = []
        self.entities.append(Entity(2, 1))
        self.entities.append(Entity(3, 1))
        self.entities.append(Entity(4, 1))
        self.entities.append(Entity(5, 3))
        self.entities.append(Entity(6, 3))
        self.entities.append(Entity(7, 4))
        self.entities.append(Entity(1, None))
        
    
        self.bad_entity = Entity(9,8) # Parent is missing
        
    def test_build_tree(self):
        
        
        tree = Tree(self.entities)
        
        self.assertTreeStructure(tree)
        
    def test_build_tree_with_bad_entity(self):
      
        # Prepare the logger  
        stream = io.StringIO()
        log = logging.getLogger()
        handler = logging.StreamHandler(stream)
        log.addHandler(handler)

        self.entities.append(self.bad_entity)
        # This should ignore the bad entity and log an error
        tree = Tree(self.entities)

        self.assertTreeStructure(tree)
        self.assertEqual(stream.getvalue(), 
                         "Error: Corrupt tree structure. Can't find parent for tree node String representation (9)!\n")

    def assertTreeStructure(self, tree):
        
        self.assertEqual(1, tree.root_node.id)
        self.assertEqual(3, len(tree.root_node.children))
        self.assertEqual(0, len(tree.root_node.children[0].children))
        self.assertEqual(2, len(tree.root_node.children[1].children))
        self.assertEqual(1, len(tree.root_node.children[2].children))
        self.assertEqual(5, tree.root_node.children[1].children[0].id)
        self.assertEqual(6, tree.root_node.children[1].children[1].id)
        self.assertEqual(7, tree.root_node.children[2].children[0].id)
        
    def test_tree_node(self):
        
        tree = Tree(self.entities)
        node = tree.get_by_id(7)
        self.assertEqual(7, node.id)
        with pytest.raises(NoSuchNodeException):
            tree.get_by_id(67)

    def test_find_by_id(self):
        
        self.assertEqual("String representation (2)", "%s" % Node(self.entities[0]))

    def test_tree_node_illegal_adding(self):
        
        exception_thrown = False
        try:
            Node(self.entities[0]).add_child(Node(self.entities[1]))
        except InvalidChildException:
            exception_thrown = True
        self.assertTrue(exception_thrown)
        
    def test_filtering(self):
        
        visibility_matrix = {1: True, 2: False, 3: True, 4: False, 5: False,
                             6: True, 7: False}
        tree = Tree(self.entities)
        for i in range(1, 8):
            node = tree.get_by_id(i)
            self.assertTrue(node.visible)
            
        tree.apply_filter("(6)")
        for i in range(1, 8):
            node = tree.get_by_id(i)
            self.assertEqual(visibility_matrix[i], node.visible)
        

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
