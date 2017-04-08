'''
Created on 01.02.2015

@author: michael
'''
from datetime import date
import re

def expand_id(id):
    '''
    Returns the basename of the file. 
    '''
    base = "%d" % id
    while len(base) < 8:
        base = "0%s" % base
    return base

class InvalidDateException(Exception):
    '''
    Exception for invalid AlexDate and AlexDateRanges.
    '''
    def __init__(self, message):
        super().__init__(message)

class InvalidChildException(Exception):
    '''
    Exception thrown when building the systematic tree
    fails.
    '''
    def __init__(self):
        super().__init__("This is not a child!")

class NoSuchNodeException(Exception):
    '''
    Exception when a tree node is not found
    '''    
    def __init__(self, identifier):
        '''
        Sets the identifier for the node not found.
        '''
        # pylint: disable=super-init-not-called
        self.identifier = identifier


def _extract_sequence_number(key):
    '''
    Extracts the last two digits of the key as integer.
    '''
    key_as_string = "%d" % key
    return int(key_as_string[-2:])

def alex_date_from_key(key):
    '''
    Creates a AlexDate object from an event key.
    '''
    key_as_string = "%010d" % key
    year = int(key_as_string[0:4])
    month = int(key_as_string[4:6])
    if month == 0:
        month = None
    day = int(key_as_string[6:8])
    if day == 0:
        day = None
    return AlexDate(year, month, day)

class AlexDate:
    ''' This is a value object for dates. It may not be changed after creation.
    It is allowed to have an empty day or an empty day and month field.
    '''
    MONTHS = (None, _('January'), _('February'), _('March'),
              _('April'), _('May'), _('June'), _('July'), _('August'),
              _('September'), _('October'), _('November'),
              _('Dezember'))

    def __init__(self, year, month=None, day=None):
        self._year = year
        self._month = month
        self._day = day
        self._validate()

    def _get_day(self):
        ''' Private getter for day'''
        return self._day

    def _get_month(self):
        ''' Private getter for month'''
        return self._month

    def _get_year(self):
        ''' Private getter for year'''
        return self._year

    def _validate(self):
        ''' Runs internal validation'''
        self._validate_year()
        self._validate_month()
        self._validate_day()
        self._validate_combined()

    def _validate_year(self):
        ''' Year has to be an integer and between 0 and 3000.
        Yes, you can't use years BC.'''
        if not self._year:
            raise InvalidDateException("Year may not be None!")
        if not isinstance(self._year, int):
            raise InvalidDateException("%s is not a valid year!"
                                       % self._year)
        if self._year < 0 or self._year > 3000:
            raise InvalidDateException("Year %d is out of range (0-3000)!"
                                       % self._year)

    def _validate_month(self):
        ''' Month must be an integer and between 0 and 13'''
        if not self._month:
            return
        if not isinstance(self._month, int):
            raise InvalidDateException("%s is not a valid month!" % 
                                       self._month)
        if self._month < 1 or self._month > 12:
            raise InvalidDateException("Month %d is out of range (1-12)!" % 
                                       self._month)

    def _validate_day(self):
        ''' Day must be an integer and between 0 and 32'''
        if not self._day:
            return
        if not isinstance(self._day, int):
            raise InvalidDateException("%s is not a valid day!" % 
                                       self._day)
        if self.day < 1 or self.day > 31:
            raise InvalidDateException("Day %d is out of range (1-31)!" % 
                                       self._day)

    def _validate_combined(self):
        ''' Creates a date object and checks for an exception.'''
        if not self._day or not self._month:
            return

        try:
            date(self._year, self._month, self._day)
        except ValueError:
            raise InvalidDateException("Illegal date: %d.%d.%d!" % 
                                       (self._day, self._month, self._year))

    def as_key(self, sequence_number):
        '''
        Returns the as an event database key with the given
        sequence number.
        TODO: Should probably me moved to the event dao.
        '''
        if not self.month:
            return int("%04d0000%02d" % (self.year, sequence_number))
        if not self.day:
            return int("%04d%02d00%02d" % 
                       (self.year, self.month, sequence_number))
        return int("%04d%02d%02d%02d" % 
                   (self.year, self.month, self.day, sequence_number))

    def __str__(self):
        if self.day:
            return "%d. %s %d" % (self.day,
                                  self.MONTHS[self.month],
                                  self.year)
        elif self.month:
            return "%s %d" % (self.MONTHS[self.month],
                              self.year)
        else:
            return "%d" % (self.year)

    def __eq__(self, other):
        if other is None:
            return False
        if self.day != other.day:
            return False
        if self.month != other.month:
            return False
        if self.year != other.year:
            return False
        return True

    def __lt__(self, other):
        # pylint: disable=too-many-return-statements
        if self._year < other.year:
            return True
        if self.year > other.year:
            return False
        # years are equal
        if self._month is None and other.month is not None:
            return True
        if self._month is None and other.month is None:
            return False
        # self._month is definitely not None
        if other.month is None:
            return False
        if self._month < other.month:
            return True
        if self._month > other.month:
            return False
        # years and months are equal
        if self._day is None and other.day is not None:
            return True
        if self._day is None and other.day is None:
            return False
        # self._day is definitely not None
        if other.day is None:
            return False
        if self._day < other.day:
            return True
        return False

    def __gt__(self, other):
        return not self == other and not self < other

    def __le__(self, other):
        return not self > other

    def __ge__(self, other):
        return not self < other


    day = property(_get_day)
    month = property(_get_month)
    year = property(_get_year)

class AlexDateRange():
    '''
    Represents a date or a date range. Currently it also contains a sequence
    number.
    TODO: Remove sequence number from AlexDateRange
    '''
    def __init__(self, start, end):
        '''
        Double typed constructor: You can either pass in AlexDate objects
        or date keys. The first use case is typically when instantiating
        in code, the second case when instantiating from database
        '''
        if isinstance(start, AlexDate):
            self.start_date = start
            self.end_date = end
            self.sequence_number = None
        else:
            self.start_date = alex_date_from_key(start)
            self.end_date = None
            if end:
                self.end_date = alex_date_from_key(end)
            self.sequence_number = _extract_sequence_number(start)

    def get_key(self):
        '''
        Generates an event key.
        TODO: Remove key selection from AlexDateRange. This should not happen
        here but in the event dao
        '''
        return self.start_date.as_key(self.sequence_number)

    def __str__(self):
        if self.end_date:
            return "%s - %s" % (self.start_date, self.end_date)
        else:
            return "%s" % self.start_date

    def __eq__(self, other):
        if other is None:
            return False
        return self.start_date == other.start_date\
            and self.end_date == other.end_date

class GenericFilter:
    '''
    Base class for filter objects
    '''
    def __init__(self):
        self.searchterms = []
        self.combine_searchterms_by_or = True
        self.case_sensitive = True

class DocumentFilter(GenericFilter):
    '''
    A filter object for documents
    '''
    def __init__(self):
        super().__init__()
        self.location = None
        self.filetype = None
        self.document_type = None
        self.start_date = None
        self.end_date = None

class EventFilter(GenericFilter):
    '''
    A filter object for events
    '''
    def __init__(self):
        super().__init__()
        self.earliest_date = None
        self.latest_date = None
        self.local_only = False
        self.unverified_only = False

class DocumentEventReferenceFilter(DocumentFilter, EventFilter):

    pass

class Entity():
    '''
    An abstract class for entities
    '''

    def __init__(self, entity_id=None):
        self._id = entity_id

    def _get_id(self):
        ''' Private setter for id.'''
        return self._id

    def __eq__(self, other):
        if other is None:
            return False
        return self._id == other.id

    def __hash__(self):
        return self._id

    # pylint: disable=invalid-name
    id = property(_get_id)

class Creator(Entity):
    '''
    A class with a stupid name. Represents the user
    that created a document or an event entry.
    '''
    def __init__(self, creator_id=None):
        Entity.__init__(self, creator_id)
        self.name = None
        self.visible = None

    def __str__(self):
        return self.name

class DocumentType(Entity):
    ''' Data entity for the document type '''
    def __init__(self, document_type_id=None):
        Entity.__init__(self, document_type_id)
        self.description = None

    def __str__(self):
        return self.description

class MainTableEntity(Entity):
    '''
    Another abstract class that provides common functionality
    for documents and events.
    '''

    def __init__(self, main_table_entity_id=None):
        Entity.__init__(self, main_table_entity_id)
        self.description = ''
        self.erfasser = None
        self.creation_date = None
        self.change_date = None

    def __hash__(self):
        # pylint: disable=broad-except
        hash_value = super().__hash__()
        if not hash_value:
            hash_value = self.description.__hash__()
        return hash_value

class Event(MainTableEntity):
    '''
    Entity class representing an event in the chronology.
    '''

    def __init__(self, event_id=None):
        MainTableEntity.__init__(self, event_id)
        self.daterange = None
        self.status_id = 0
        self.location_id = 0

    def __str__(self):
        return "%s: %s" % (self.daterange, self.description)

class DocumentFileInfo(Entity):
    '''
    Basic information for document files. The page property
    is not very well named. It's more of a subdocument id,
    since a document may have several document files.
    The resolution property is just for graphical files (and
    perhaps for movies). For pdf files and the like this
    property is None.
    '''

    def __init__(self, document_file_id=None):
        Entity.__init__(self, document_file_id)
        self.filetype = None
        self.resolution = None
        self.page = None
        self.document_id = None

    def get_basename(self):
        '''
        Returns the basename of the file. 
        '''
        return expand_id(self.id)
    
    def get_file_name(self):
        '''
        Build an 8 character + extension file name from
        the sub document id.
        '''
        return "%s.%s" % (self.get_basename(), self.filetype)
    
    def __str__(self):
        if self.id is None:
            return "New document file info"
        else:
            return self.get_file_name()

class Document(MainTableEntity):
    '''
    Entity representing a document. A document
    may have several files.
    '''

    def __init__(self, document_id=None):
        MainTableEntity.__init__(self, document_id)
        self.condition = ''
        self.keywords = ''
        self.document_type = None

    def __str__(self):
        if not self.id:
            return _("New document")
        try:
            return "%d: %s (%s)" % (self.id, self.description, self.document_type.description)
        except AttributeError:
            return "%d: %s" % (self.id, self.description)

class EventTypeIdentifier:
    '''
    Identifier class for event types.
    '''
    
    def __init__(self, hauptid, unterid):
        self.hauptid = hauptid
        self.unterid = unterid
        
    def __eq__(self, other):
        if other is None:
            return False
        return self.hauptid == other.hauptid and self.unterid == other.unterid

    def __lt__(self, other):
        if self.hauptid < other.hauptid:
            return True
        if self.hauptid > other.hauptid:
            return False
        return self.unterid < other.unterid
    
    def __gt__(self, other):
        return other < self

    def __ge__(self, other):
        
        return self == other or self > other
    
    def __le__(self, other):
        
        return self == other or self < other
        
    def __hash__(self):
        return hash((self.hauptid, self.unterid))
    
    def _get_parent_identifier(self):
        if self.unterid != 0:
            return EventTypeIdentifier(self.hauptid, 0)
        if self.hauptid != 0:
            return EventTypeIdentifier(0, 0)
        return None

    parent_id = property(_get_parent_identifier)
    
class EventType:
    '''
    Categorizes an Event.
    '''
    def __init__(self, identifier, description):
        # pylint: disable=invalid-name
        self.id = identifier
        self.description = description
        
        
    def __str__(self):
        return self.description
    
    def __eq__(self, other):
        if other is None:
            return False
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id

    def __gt__(self, other):
        return self.id > other.id

    def __le__(self, other):
        return self == other or self.id < other.id

    def __ge__(self, other):
        return self == other or self.id > other.id

    parent_id = property(lambda self: self.id.parent_id)

class Node:
    '''
    An abstract node representation for trees.
    '''
    
    def __init__(self, entity):
        self.entity = entity
        self.parent = None
        self.children = []
        self._visible_nodes = -1
        
    def __str__(self):
        
        return "%s" % self.entity
        
    def add_child(self, child_node):
        '''
        Adds a child to a node. Throws an InvalidChildException if
        the childs node is not correct.
        '''
        if self.entity.id != child_node.parent_id:
            raise InvalidChildException()
        self.children.append(child_node)
        child_node.parent = self
        self.children.sort()
    
    def apply_filter(self, filter_string):
        '''
        Determines if this node is visible after applying the filter_string
        
        Applying means comparing if the filter_string is a substring of the
        entities string representation in upper case.
        
        Visible means that either one of the children entities is visible through the
        filter or the entity of the node itself.
        '''
        self._visible_nodes = 0
        for child in self.children:
            self._visible_nodes += child.apply_filter(filter_string)
        if self._visible_nodes > 0:
            # We are definitely visible 
            self._visible_nodes += 1
            return self._visible_nodes
        
        if filter_string in self.entity.__str__().upper():
            self._visible_nodes += 1
        return self._visible_nodes
    
    def clear_filter(self):
        '''
        Removes all filtering information from the subtree represented by this node
        '''
        for child in self.children:
            child.clear_filter()
        self._visible_nodes = -1
            
        
    def __lt__(self, other):
        
        return self.entity < other.entity
        
    parent_id = property(lambda self: self.entity.parent_id)
    # pylint: disable=invalid-name
    id = property(lambda self: self.entity.id)
    visible = property(lambda self: self._visible_nodes != 0)
    
class Tree:
    '''
    Class for generic tree building.
    
    The entities sorted into a tree must fullfill the following conditions:
    - they need a property called id
    - they need a property called parent_id
    - in the list there must be one element where parent_id is None. This
      is the root element of the tree
    - the entities must be sortable, i.e., the must implement at least __lt__
    '''
    def __init__(self, entity_list):

        self.root_node = None

        self._build_node_tree(entity_list)

    def apply_filter(self, filter_string):
        '''
        Applies a filter to the tree
        
        After that the visible property of the tree node indicates if a node
        is visible or not.
        '''
        self.clear_filter()
        return self.root_node.apply_filter(filter_string.upper())
        
    def clear_filter(self):
        '''
        Resets all filtering on the tree
        '''
        self.root_node.clear_filter()

    def get_by_id(self, identifier):
        '''
        Fetches a node by its id
        '''
        
        node = self._find_by_id(identifier, self.root_node)
        if node is None:
            raise NoSuchNodeException(identifier)
        return node
        
    def _find_by_id(self, identifier, node):
        
        if node.id == identifier:
            return node
        for child in node.children:
            found_node = self._find_by_id(identifier, child)
            if found_node:
                return found_node
        return None
        
    def _build_node_tree(self, entity_list):
        '''
        Helper method called in the constructor to build the tree.
        '''
        
        node_dictionary = self._analyze_entities(entity_list)
        
        for node in node_dictionary.values():
            if not node.parent_id is None:
                try:
                    parent_node = node_dictionary[node.parent_id]
                    parent_node.add_child(node)
                except KeyError:
                    # TODO: Log an error that the the systematic tree
                    # is not well formed in the database
                    print("Error: Can't find parent for systematic point %s!" % node)

    def _analyze_entities(self, entity_list):
        
        node_dictionary = {}
        
        for entity in entity_list:
            node = Node(entity)
            parent_id = entity.parent_id
            if parent_id is None:
                self.root_node = node
            node_dictionary[entity.id] = node

        return node_dictionary

class DocumentStatistics:
    '''
    Wrapper class for statistical information on documents
    '''
    
    def __init__(self):
        self.number_of_documents = 0
        self.number_of_files = 0
        self.number_of_files_by_type = {}
        
class PaginatedResult:
    '''
    Utility class for paginated results
    '''
    
    def __init__(self):
        self.entities = []
        self.page = 0
        self.page_size = 0
        self.number_of_pages = 0
