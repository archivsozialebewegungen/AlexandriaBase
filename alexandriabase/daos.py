'''
Created on 07.02.2018

@author: michael
'''
from threading import Lock
from sqlalchemy.sql.expression import or_, select, and_, delete, insert, update,\
    join
from sqlalchemy.sql.functions import func
from _functools import reduce

from alexandriabase import _
from alexandriabase.base_exceptions import NoSuchEntityException, DataError
from injector import inject, singleton, provider, ClassProvider, Module
from alexandriabase import baseinjectorkeys
from alexandriabase.domain import Creator, DocumentStatistics, Document,\
    DocumentFileInfo, DocumentType, AlexDateRange, Event, alex_date_from_key,\
    EventType, EventTypeIdentifier, Tree, EventStatistics
from sqlalchemy.sql.schema import Column, Table, ForeignKey, MetaData
from sqlalchemy.sql.sqltypes import Integer, String, Date
from sqlalchemy.engine import create_engine
from sqlalchemy.pool import StaticPool

CURRENT_VERSION = '0.4'

ALEXANDRIA_METADATA = MetaData()

CREATOR_TABLE = Table(
    'erfasser',
    ALEXANDRIA_METADATA,
    Column('id', Integer, primary_key=True),
    Column('name', String),
    Column('anzeige', String))
    
REGISTRY_TABLE = Table(
    'registry',
    ALEXANDRIA_METADATA,
    Column('schluessel', String, primary_key=True),
    Column('wert', String))
    
DOCUMENT_TYPE_TABLE = Table(
    'doktyp',
    ALEXANDRIA_METADATA,
    Column('id', Integer, primary_key=True),
    Column('beschreibung', String))

EVENT_TABLE = Table(
    'chrono',
    ALEXANDRIA_METADATA,
    Column('ereignis_id', Integer, primary_key=True),
    Column('ereignis', String),
    Column('ende', Integer),
    Column('status_id', Integer),
    Column('erfasser_id', Integer, ForeignKey('erfasser.id')),
    Column('aufnahme', Date),
    Column('aenderung', Date),
    Column('ort_id', Integer))

DOCUMENT_TABLE = Table(
    'dokument', ALEXANDRIA_METADATA,
    Column('hauptnr', Integer),
    Column('laufnr', Integer, primary_key=True),
    Column('seite', Integer),
    Column('beschreibung', String),
    Column('dateityp', String),
    Column('standort', String),
    Column('zustand', String),
    Column('keywords', String),
    Column('erfasser_id', Integer, ForeignKey('erfasser.id')),
    Column('aufnahme', Date),
    Column('aenderung', Date),
    Column('doktyp', Integer, ForeignKey('doktyp.id')),
    Column('res', Integer))

DOCUMENT_EVENT_REFERENCE_TABLE = Table(
    'dverweis',
    ALEXANDRIA_METADATA,
    Column('ereignis_id', 
           Integer, 
           ForeignKey('chrono.ereignis_id', ondelete="CASCADE"),
           primary_key=True),
    Column('laufnr',
           Integer,
           ForeignKey('dokument.laufnr'),
           primary_key=True))

EVENT_EVENTTYPE_REFERENCE_TABLE = Table(
    'everweis', ALEXANDRIA_METADATA,
    Column('ereignis_id', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")),
    Column('hauptid', Integer),
    Column('unterid', Integer))

EVENTTYPE_TABLE = Table(
    'ereignistyp',
    ALEXANDRIA_METADATA,
    Column('haupt', Integer),
    Column('unter', Integer),
    Column('beschreibung', String))

EVENT_CROSS_REFERENCES_TABLE = Table(
    'qverweis',
    ALEXANDRIA_METADATA,
    Column('id1', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")),
    Column('id2', Integer, ForeignKey('chrono.ereignis_id', ondelete="CASCADE")))

JOINS = {DOCUMENT_TABLE: 
            {DOCUMENT_EVENT_REFERENCE_TABLE: join(DOCUMENT_TABLE,
                                                  DOCUMENT_EVENT_REFERENCE_TABLE,
                                                  isouter=True)}
        }

def get_foreign_keys(primary_key):
    '''
    Returns the foreign keys that reference a certain primary key.
    '''
    foreign_keys = []
    for table_name in ALEXANDRIA_METADATA.tables:
        table = ALEXANDRIA_METADATA.tables[table_name]
        for foreign_key in table.foreign_keys:
            if foreign_key.column == primary_key:
                foreign_keys.append(foreign_key.parent)
    return foreign_keys

def get_join_tables_from_expression(expression, default, join_tables):
    
    if expression is None:
        return join_tables
    
    if hasattr(expression, '_from_objects') and expression._from_objects:
        for table in expression._from_objects:
            if table != default:
                join_tables.add(table)
    
    if hasattr(expression, 'clauses') and expression.clauses:
        for clause in expression.clauses:
            join_tables = get_join_tables_from_expression(clause, default, join_tables)
    
    return join_tables

def get_joins_for_expression(expression, from_table):
    
    joins = []
    for join_table in get_join_tables_from_expression(expression, from_table, set()):
        joins.append(JOINS[from_table][join_table])
        
    return joins

def combine_expressions(expressions, method):
    '''
    Combines the different expressions with and.
    '''
    if not expressions:
        return None
    if len(expressions) == 1:
        return expressions[0]
    # pylint: disable=unnecessary-lambda
    return reduce(lambda e1, e2: method(e1, e2), expressions)


class NestedTransactionsException(Exception):
    '''
    Currently we do not allow nested transactions. When this is
    tried, raise this exception.
    '''
    pass

class GenericFilterExpressionBuilder:
    '''
    Has common functinality for filter expression builders for
    documents and events
    '''
    def __init__(self):
        self.table = None
        self.textcolumn = None
        self.expressions = []
        self.lock = Lock()

    def create_filter_expression(self, filter_object):
        '''
        Creates the expression
        '''
        with self.lock:
            self.expressions = []
            self._create_expressions(filter_object)
            return combine_expressions(self.expressions, and_)

    def _create_expressions(self, filter_object):
        '''
        Creates the different filter expressions that then will be combined
        with and. Should be expanded in child classes.
        '''
        self._append_expression(self._build_searchterm_expression(filter_object))

    def _append_expression(self, expression):
        '''
        Adds an expression (if it is not None) to the list of expressions
        that will be combined with 'and' in the end.
        '''
        if not isinstance(expression, type(None)):
            self.expressions.append(expression)

    def _build_searchterm_expression(self, filter_object):
        '''
        Builds the sql alchemy expression for the search terms
        '''
        subexpression_list = self._build_searchterm_expressions(filter_object)
        if filter_object.combine_searchterms_by_or:
            self._append_expression(combine_expressions(subexpression_list, or_))
        else:
            self._append_expression(combine_expressions(subexpression_list, and_))

    def _build_searchterm_expressions(self, filter_object):
        '''
        Evaluates the searchterms.
        '''
        searchterm_expressions = []
        for searchterm in filter_object.searchterms:
            if searchterm != None and searchterm != '':
                if filter_object.case_sensitive:
                    searchterm_expressions.append(
                        self.textcolumn.contains(searchterm))
                else:
                    # We can't use pythons upper() function here because the
                    # database might have another implementation than python
                    # postgres: ß -> ß, Python: ß -> SS
                    searchterm_expressions.append(
                        func.upper(self.textcolumn).contains(func.upper(searchterm)))
        return searchterm_expressions


class GenericDao:
    '''
    Common functionality for all daos
    '''

    def __init__(self, db_engine):
        self.db_engine = db_engine
        self.transactional_connection = None
        self.transaction_level = 0
        self.transaction = None
        
    def _get_connection(self):
        '''
        Returns a new connection, if no transaction is running,
        else returns the transactional connection.
        '''
        if self.transactional_connection != None:
            return self.transactional_connection
        return self.db_engine.connect()

    def transactional(self, function, *args, **kwargs):
        '''
        Method to run a method transactional.
        '''
        if self.transactional_connection is None:
            self.transactional_connection = self.db_engine.connect()
            self.transaction = self.transactional_connection.begin()
            self.transaction_level = 1
        else:
            self.transaction_level += 1
            
        try:
            return_value = function(*args, **kwargs)
            if self.transaction_level == 1:
                self.transaction.commit()
                self.transactional_connection = None
                self.transaction_level = 0
            else:
                self.transaction_level -= 1
            return return_value
        except:
            self.transaction.rollback()
            self.transactional_connection = None
            self.transaction_level = 0
            raise

    def _get_exactly_one_row(self, query):
        '''
        Helper method that expects a query to return
        exactly one row.
        '''

        result = self.connection.execute(query)
        row = result.fetchone()
        result.close()

        if not row:
            raise NoSuchEntityException("Did not find entity for query '%s'" % query)

        return row

    def _get_one_row_or_none(self, query):
        '''
        Helper method to get not more than one row from query
        '''

        result = self.connection.execute(query)
        row = result.fetchone()
        result.close()

        if not row:
            return None

        return row

    connection = property(_get_connection)

class EntityDao(GenericDao):
    '''
    Common functionality for all daos
    '''

    def __init__(self, db_engine, table):
        super().__init__(db_engine)
        self.table = table
        primary_keys = table.primary_key.columns
        if len(primary_keys) != 1:
            raise DataError("Entity table needs exactly one primary key. " +
                            "Use GenericDao for table {}." . format(table))
        key_key = primary_keys.keys()[0]
        self.primary_key = primary_keys[key_key]
        self.select_column = self.primary_key
        self.foreign_keys = get_foreign_keys(self.primary_key)
    
    def _get_exactly_one(self, query):
        '''
        Gets exactly one entity from the database, throws exception
        when no result is found.
        '''

        row = self._get_exactly_one_row(query)

        return self._row_to_entity(row)

    def _get_one_or_none(self, query):
        '''
        Get one entity from the database, the result may also be
        empty.
        '''

        row = self._get_one_row_or_none(query)

        if row is None:
            return None

        return self._row_to_entity(row)

    def _get_list(self, query):
        '''
        Execute a query that returns a list.
        '''

        result = self.connection.execute(query)
        rows = result.fetchall()
        result.close()

        return self._rows_to_entities(rows)

    def _row_to_entity(self, row):
        '''
        Dummy method to overwrite in child class.
        '''
        # pylint: disable=unused-argument
        # pylint: disable=no-self-use
        raise Exception("Implement in child class.")

    def _rows_to_entities(self, rows):
        '''
        Returns a list of entities for a list of rows.
        '''
        entities = []
        for row in rows:
            entities.append(self._row_to_entity(row))
        return entities

    def get_by_id(self, entity_id):
        ''' Get an entity by id. Throws exception when the entity does not exist.'''
        query = select([self.table])\
            .where(self.primary_key == entity_id)
        return self._get_exactly_one(query)

    def get_first(self, filter_expression=None):
        ''' Get the first entity or None if no entity exists or is allowed by filter.'''
        return self._goto_absolute(func.min, filter_expression)
    
    def get_last(self, filter_expression=None):
        ''' Get the last entity or None if no entity exits or is allowed by filter.'''
        return self._goto_absolute(func.max, filter_expression)
    
    def _goto_absolute(self, function, filter_expression):
        subquery = select([function(self.select_column)])
        for join in get_joins_for_expression(filter_expression, self.table):
            subquery = subquery.select_from(join)    
        if filter_expression is not None:
            subquery = subquery.where(filter_expression)
        query = select([self.table])\
            .where(self.primary_key == subquery.scalar_subquery())  # @UndefinedVariable
            
        return self._get_one_or_none(query)

    def get_next(self, entity, filter_expression=None):
        ''' Get the next entity or the first, if it is the last'''
        return self._goto_relative(self.select_column > entity.id, func.min, filter_expression, self.get_first)

    def get_previous(self, entity, filter_expression=None):
        ''' Get the previous entity or the last, if it is the first'''
        return self._goto_relative(self.select_column < entity.id, func.max, filter_expression, self.get_last)

    def get_nearest(self, entity_id, filter_expression=None):
        ''' Get the entity matching the id, or, if not existing,
        the next entity after this id. If this does not provide
        an entity, get the last entity.'''
        return self._goto_relative(self.select_column >= entity_id, func.min, filter_expression, self.get_last)

    def _goto_relative(self, condition, function, filter_expression, alternative):

        subquery = select([function(self.select_column)])
        for join in get_joins_for_expression(filter_expression, self.table):
            subquery = subquery.select_from(join)    
        if filter_expression is not None:
            condition = and_(condition, filter_expression)
        subquery = subquery.where(condition)

        query = select([self.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        entity = self._get_one_or_none(query)
        
        if not entity:
            return alternative(filter_expression)
        return entity

    def save(self, entity):
        '''
        Decides on the existence of the entity.id, if an update
        or an insert is necessary and executes the appropriate
        method in a transaction.
        '''
        if entity.id:
            return self.transactional(self._update, entity)
        return self.transactional(self._insert, entity)

    def delete(self, entity_id):
        '''
        Public wrapper method to perform deletion of entity transactional.
        '''

        self.transactional(self._delete, entity_id)
        
    def _update(self, entity):
        '''
        Runs an update on an already existing entity. Returns the id
        of the updated entity.
        '''
        # pylint: disable=no-self-use
        # pylint: disable=unused-argument
        raise Exception("Implement in child class")

    def _insert(self, entity):
        '''
        Persists an entity not yet existing. Returns the id of the
        inserted entity.
        '''
        # pylint: disable=no-self-use
        # pylint: disable=unused-argument
        raise Exception("Implement in child class")

    def _delete_references(self, entity_id):
        '''
        Deletes the references to an entity.
        '''
        for foreign_key in self.foreign_keys:
            query = delete(foreign_key.table).where(foreign_key == entity_id)
            self.connection.execute(query)

    def _delete(self, entity_id):
        '''
        Deletes an entity and all its references.
        '''
        self._delete_references(entity_id)
        query = delete(self.table)\
            .where(self.primary_key == entity_id)
        self.connection.execute(query)

    def _get_next_id(self):
        '''
        As long as we do not have sequences, load the id
        this way.
        '''
        function = func.max(self.primary_key)
        result = self.connection.execute(select([function]))
        return result.fetchone()[0] + 1

    def get_count(self, where_expression=None):
        '''
        Counts the rows in a table. The where expression is optional.
        '''
        query = select([func.count()]).select_from(self.table)
        if not where_expression is None:
            query = query.where(where_expression)
        row = self._get_exactly_one_row(query)
        return row[0]

    def find(self, condition=None, page=None, page_size=1):
        '''
        Searches in the database and returns a paginated result.
        pages starts with 1. If no page is given, all will be
        returned
        '''
            
        query = select([self.table]).\
            order_by(self.primary_key)
        if not page is None:
            offset = (page - 1) * page_size
            query = query.offset(offset).limit(page_size) 
        if not condition is None:
            query = query.where(condition)
        return self._get_list(query)

class CachingDao(EntityDao):
    '''
    Mixin class for caching daos.
    '''
    # pylint: disable=no-member
    
    def __init__(self, db_engine, table):
        super().__init__(db_engine, table)
        self.cache = {}
    
    def clear_cache(self):
        '''
        Clears the cache
        '''
        # pylint: disable=attribute-defined-outside-init
        self.cache = {}

    def find(self, condition=None, page=None, page_size=1):
        entity_list = super().find(condition, page, page_size)
        return self._cache_list(entity_list)
    
    def get_by_id(self, entity_id):
        
        if entity_id in self.cache:
            return self.cache[entity_id]
        entity = super().get_by_id(entity_id)
        self.cache[entity_id] = entity
        return entity
    
    def delete(self, entity_id):
        del self.cache[entity_id]
        super().delete(entity_id)
        
    def save(self, entity):
        entity = super().save(entity)
        self.cache[entity.id] = entity
        return entity
        
    def _cache_list(self, entity_list):
        '''
        Puts the elements in the list into the cache
        '''
        for entity in entity_list:
            self.cache[entity.id] = entity
        return entity_list

class BasicCreatorProvider(object):
    '''
    This basic implementation of a creator provider
    always return the admin as creator. This is a
    creator provider for automated scripts etc. Interactive
    applications should provide their own implementations
    that return the current user.
    '''
    @inject
    def __init__(self, creator_dao: baseinjectorkeys.CREATOR_DAO_KEY):
        self.creator_dao = creator_dao

    def _get_creator(self):
        ''' Private getter to use in property.'''
        creator = self.creator_dao.find_by_name("Admin")
        if creator is None:
            creator = Creator()
            creator.name = "Admin"
            creator.visible = False
            creator = self.creator_dao.save(creator)
        return creator

    creator = property(_get_creator)

class CreatorDao(CachingDao):
    '''
    Reads users from the database
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        super().__init__(db_engine, CREATOR_TABLE)
        self.cache = {}



    # pylint: disable=arguments-differ
    def get_by_id(self, creator_id):

        if creator_id in self.cache:
            return self.cache[creator_id]

        query = select([self.table])\
            .where(self.primary_key == creator_id)  # @UndefinedVariable
        creator = self._get_exactly_one(query)
        self.cache[creator.id] = creator
        return creator

    def find_by_name(self, name):
        '''
        Surprisingly finds the creator by name.
        '''
        for creator_id in self.cache:
            if name == self.cache[creator_id].name:
                return self.cache[creator_id]
        query = select([self.table]).where(self.table.c.name == name)
        creator = self._get_one_or_none(query)
        if creator != None:
            self.cache[creator.id] = creator
        return creator

    def find_all_visible(self):
        '''
        Returns all creators where the flag for visibility is set.
        '''
        return self.find(self.table.c.anzeige == 'y')

    # pylint: disable=arguments-differ
    def _update(self, creator):
        query = update(self.table)\
            .values(name=creator.name,
                    anzeige=creator.visible)\
            .where(self.table.c.id == creator.id)
        self.connection.execute(query)
        return creator

    # pylint: disable=arguments-differ
    def _insert(self, creator):
        # pylint: disable=protected-access
        creator._id = self._get_next_id()
        query = insert(self.table).values(
            id=creator.id,
            name=creator.name,
            anzeige=creator.visible)
        self.connection.execute(query)
        return creator

    def _row_to_entity(self, row):
        erfasser = Creator(row[self.table.c.id])
        erfasser.name = row[self.table.c.name]
        erfasser.visible = row[self.table.c.anzeige] == 'y'
        return erfasser

class DocumentFilterExpressionBuilder(GenericFilterExpressionBuilder):
    '''
    Creates a document filter expression for sql alchemy from a
    document filter object.
    '''
    def __init__(self):
        super().__init__()
        self.table = DOCUMENT_TABLE
        self.textcolumn = self.table.c.beschreibung

    # pylint: disable=arguments-differ
    def _create_expressions(self, document_filter):
        super()._create_expressions(document_filter)
        self._append_expression(self._build_signature_expression(document_filter))
        self._append_expression(self._build_filetype_expression(document_filter))
        self._append_expression(self._build_document_type_expression(document_filter))
        self._append_expression(self._build_missing_event_link_expression(document_filter))
        
    def _build_missing_event_link_expression(self, document_filter):
        
        if not document_filter.missing_event_link:
            return None
        
        return and_(DOCUMENT_EVENT_REFERENCE_TABLE.c.ereignis_id.is_(None),
                    DOCUMENT_TABLE.c.seite == 1)            
        
    def _build_signature_expression(self, document_filter):
        '''
        Creates a signature expression.
        '''
        if not document_filter.signature:
            return None
        signature = document_filter.signature.upper()
        return or_(self.table.c.standort == signature,
                   self.table.c.standort.startswith("%s." % signature))

    def _build_filetype_expression(self, document_filter):
        '''
        Creates a filetype expression.
        '''
        if not document_filter.filetype:
            return None
        subquery = select([self.table.c.hauptnr]).\
            where(self.table.c.dateityp == document_filter.filetype)
        return self.table.c.hauptnr.in_(subquery)

    def _build_document_type_expression(self, document_filter):
        '''
        Creates a filetype expression.
        '''
        if not document_filter.document_type:
            return None
        subquery = select([self.table.c.hauptnr]).where(
            self.table.c.doktyp == document_filter.document_type)
        return self.table.c.laufnr.in_(subquery)

class DocumentDao(EntityDao):
    '''
    Persistance for the Document domain entity.
    '''

    @inject
    def __init__(self,
                 db_engine: baseinjectorkeys.DB_ENGINE_KEY,
                 config: baseinjectorkeys.CONFIG_KEY,
                 creator_dao: baseinjectorkeys.CREATOR_DAO_KEY,
                 document_type_dao: baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY,
                 creator_provider: baseinjectorkeys.CREATOR_PROVIDER_KEY):
        # pylint: disable=too-many-arguments
        super().__init__(db_engine, DOCUMENT_TABLE)
        self.select_column = DOCUMENT_TABLE.c.hauptnr
        self.config = config
        self.creator_dao = creator_dao
        self.document_type_dao = document_type_dao
        self.creator_provider = creator_provider

        
    def _generate_query_from_subquery(self, subquery):
        where_clause = self.primary_key == subquery
        return select([self.table]).where(where_clause)

    def _get_one_or_last(self, subquery, filter_expression):
        query = self._generate_query_from_subquery(subquery)
        document = self._get_one_or_none(query)
        if document is None:
            return self.get_last(filter_expression)
        return document

    # pylint: disable=arguments-differ
    def _delete(self, document_id):
        '''
        Deletes all rows pertaining to the given document.
        Before using this method you should consider to
        delete the document files using the document file
        manager and perhaps deleting the document file infos
        using the document file info dao.
        '''
        self._delete_references(document_id)
        delete_statement = delete(self.table).where(self.table.c.hauptnr == document_id)
        self.connection.execute(delete_statement)

    def _row_to_entity(self, row):

        dokument = Document(row[self.table.c.laufnr])
        dokument.description = row[self.table.c.beschreibung]
        dokument.condition = row[self.table.c.zustand]
        dokument.keywords = row[self.table.c.keywords]
        dokument.creation_date = row[self.table.c.aufnahme]
        dokument.change_date = row[self.table.c.aenderung]
        erfasser_id = row[self.table.c.erfasser_id]
        dokument.erfasser = self.creator_dao.get_by_id(erfasser_id)
        dokument.document_type = self.document_type_dao.get_by_id(row[self.table.c.doktyp])
        return dokument

    # pylint: disable=arguments-differ
    def _update(self, document):
        update_statement = update(DOCUMENT_TABLE).\
        where(self.table.c.laufnr == document.id).\
        values(beschreibung=document.description,
               zustand=document.condition,
               keywords=document.keywords,
               doktyp=document.document_type.id,
               aenderung=func.now())
        self.connection.execute(update_statement)
        return document

    # pylint: disable=arguments-differ
    def _insert(self, document):
        # pylint: disable=protected-access
        document._id = self._get_next_id()
        document.erfasser = self.creator_provider.creator
        insert_statement = insert(DOCUMENT_TABLE).\
            values(hauptnr=document.id,
                   laufnr=document.id,
                   beschreibung=document.description,
                   zustand=document.condition,
                   keywords=document.keywords,
                   erfasser_id=document.erfasser.id,
                   doktyp=document.document_type.id,
                   aufnahme=func.now(),
                   aenderung=func.now())
        self.connection.execute(insert_statement)
        return document

    def get_statistics(self):
        '''
        Returns statistical information on the documents in the database
        '''
        
        statistics = DocumentStatistics()
        statistics.number_of_files = self.get_count()
        statistics.number_of_documents = self.get_count(self.table.c.hauptnr == self.table.c.laufnr)
        for file_type in self.config.filetypes:
            count = self.get_count(self.table.c.dateityp == file_type)
            if count > 0:
                statistics.number_of_files_by_type[file_type] = count
        return statistics
    
    def find(self, condition=None, page=None, page_size=1):
        
        extended_expression = self.table.c.hauptnr == self.table.c.laufnr
        if not condition is None:
            extended_expression = and_(extended_expression, condition)
        
        return super().find(extended_expression, page, page_size) 

class DocumentFileInfoDao(EntityDao):
    '''
    Dao for the document files. At the moment
    needs to use the document table also used
    by the document dao, because the data of these
    two are mixed into one table.
    '''

    @inject
    def __init__(self,
                 db_engine: baseinjectorkeys.DB_ENGINE_KEY,
                 creator_provider: baseinjectorkeys.CREATOR_PROVIDER_KEY):
        super().__init__(db_engine, DOCUMENT_TABLE)
        self.creator_provider = creator_provider
        self.table = DOCUMENT_TABLE

    # pylint: disable=arguments-differ
    def get_by_id(self, document_file_id):
        query = select([self.table])\
            .where(and_(self.table.c.laufnr == document_file_id,  
                        self.table.c.seite != None))  
        return self._get_exactly_one(query)

    def get_file_infos_for_document(self, document_id):
        '''
        Gets a list of all the document files for a certain document.
        '''
        query = select([self.table]).where(
            and_(self.table.c.hauptnr == document_id,  
                 self.table.c.seite != None)).\
                 order_by(self.table.c.seite)  
        return self._get_list(query)

    def create_new_file_info(self, document_id, filetype=None, resolution=None):
        '''
        Transaction wrapper method for _create_new_file_info.
        '''
        return self.transactional(
            self._create_new_file_info,
            document_id, filetype, resolution)

    def _create_new_file_info(self, document_id, filetype, resolution):
        '''
        Creates a new entry into the document table for this document file.
        '''
        page = self._get_next_page(document_id)
        if page == 1:
            file_info = DocumentFileInfo(document_id)
        else:
            file_info = DocumentFileInfo()
        file_info.document_id = document_id
        file_info.page = page
        file_info.filetype = filetype
        file_info.resolution = resolution
        return self.save(file_info)

    def _get_next_page(self, document_id):
        '''
        Searches for the bigges page number and adds 1.
        '''
        function = func.max(self.table.c.seite)  
        query = select([function])\
        .where(self.table.c.hauptnr == document_id)  
        row = self._get_exactly_one_row(query)
        if row[0] is None:
            return 1
        return row[0] + 1  

    def _get_next_id(self):
        '''
        Searches for the maximum id and adds 1.
        '''
        query = select([func.max(self.table.c.laufnr)])  
        row = self._get_exactly_one_row(query)
        return row[0] + 1  

    # pylint: disable=arguments-differ
    def _insert(self, file_info):
        # pylint: disable=protected-access
        file_info._id = self._get_next_id()
        insert_statement = insert(self.table).values(
            hauptnr=file_info.document_id,
            laufnr=file_info.id,
            erfasser_id=self.creator_provider.creator.id,
            seite=file_info.page,
            res=file_info.resolution,
            dateityp=file_info.filetype,
            aufnahme=func.now(),
            aenderung=func.now())
        self.connection.execute(insert_statement)
        return file_info

    # pylint: disable=arguments-differ
    def _update(self, file_info):
        update_statement = update(self.table).\
            where(self.table.c.laufnr == file_info.id).\
            values(hauptnr=file_info.document_id,
                   erfasser_id=self.creator_provider.creator.id,
                   seite=file_info.page,
                   res=file_info.resolution,
                   dateityp=file_info.filetype,
                   aenderung=func.now())
        self.connection.execute(update_statement)
        return file_info

    # pylint: disable=arguments-differ
    def _delete(self, document_file_id):
        '''
        Deletes a file info. Might result in deleting a record,
        but also may update the master document record and set
        the page to 0, if it is the last document file for
        the document entry.
        '''
        try:
            info = self.get_by_id(document_file_id)
        except NoSuchEntityException:
            # Already deleted or did not exist in the first place
            return
        if info.document_id == info.id:
            update_statement = update(self.table).where(
                self.table.c.laufnr == info.id  
            ).values(seite=None)
            self.connection.execute(update_statement)
        else:
            delete_statement = delete(self.table).where(
                self.table.c.laufnr == info.id  
            )
            self.connection.execute(delete_statement)

    def _row_to_entity(self, row):
        info = DocumentFileInfo(row[self.table.c.laufnr])  
        info.document_id = row[self.table.c.hauptnr]  
        info.resolution = row[self.table.c.res]  
        info.filetype = row[self.table.c.dateityp]  
        info.page = row[self.table.c.seite]  
        return info

class DocumentTypeDao(CachingDao):
    '''
    Dao for document types.
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        super().__init__(db_engine, DOCUMENT_TYPE_TABLE)

    def _row_to_entity(self, row):
        entity = DocumentType(row[self.table.c.id])
        entity.description = row[self.table.c.beschreibung]
        return entity 

    def get_all(self):
        '''
        Returns all document types from the cache. If the cache
        is empty loads the cache.
        '''
        return self.find()

class EventCrossreferencesDao(GenericDao):
    '''
    Handles the crossreferences between events.
    '''
    
    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
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

    @inject
    def __init__(self,
                 db_engine: baseinjectorkeys.DB_ENGINE_KEY,
                 creator_dao: baseinjectorkeys.CREATOR_DAO_KEY,
                 references_dao: baseinjectorkeys.RELATIONS_DAO_KEY,
                 eventtype_dao: baseinjectorkeys.EVENT_TYPE_DAO_KEY,
                 creator_provider: baseinjectorkeys.CREATOR_PROVIDER_KEY):
        '''
        Constructor with a lot of dependency injection.
        '''
        # pylint: disable=too-many-arguments
        super().__init__(db_engine, EVENT_TABLE)
        self.creator_dao = creator_dao
        self.references_dao = references_dao
        self.eventtype_dao = eventtype_dao
        self.creator_provider = creator_provider

    # pylint: disable=arguments-differ
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

    # pylint: disable=arguments-differ
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
    
    def get_statistics(self):
        '''
        Returns statistical information on the documents in the database
        '''
        
        statistics = EventStatistics()
        statistics.number_of_events = self.get_count()
        return statistics


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
    
class RegistryDao(GenericDao):
    '''
    Reads and writes keys / value pairs from the database
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        super().__init__(db_engine)
        self.table = REGISTRY_TABLE

    def get(self, key):
        '''
        Get a value for the given key. If the key does
        not exist the method returns None
        '''

        query = select([self.table])\
            .where(self.table.c.schluessel == key)
        row = self._get_one_row_or_none(query)
        if row is None:
            return row
        return row[self.table.c.wert]
    
    def set(self, key, value):
        '''
        Saves the key value / pair in the database
        '''
        old_value = self.get(key)
        if old_value is None:
            self._insert(key, value)
        else:
            self._update(key, value)

    def _update(self, key, value):
        query = update(self.table)\
            .values(wert=value)\
            .where(self.table.c.schluessel == key)
        self.connection.execute(query)

    def _insert(self, key, value):
        query = insert(self.table).values(
            schluessel=key,
            wert=value)
        self.connection.execute(query)

class DocumentEventRelationsDao(GenericDao):
    '''
    Handles all kinds of relations
    '''
    
    @inject
    def __init__(self, 
                 db_engine:
                 baseinjectorkeys.DB_ENGINE_KEY,
                 document_filter_expression_builder:
                 baseinjectorkeys.DOCUMENT_FILTER_EXPRESSION_BUILDER_KEY,
                 event_filter_expression_builder:
                 baseinjectorkeys.EVENT_FILTER_EXPRESSION_BUILDER_KEY):
        super().__init__(db_engine)
        self.deref_table = DOCUMENT_EVENT_REFERENCE_TABLE
        self.doc_table = DOCUMENT_TABLE
        self.event_table = EVENT_TABLE
        self.doc_filter_expression_builder = document_filter_expression_builder
        self.event_filter_expression_builder = event_filter_expression_builder
        
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
    
    def fetch_doc_event_references(self, document_event_reference_filter):
        '''
        Fetches a dictionary with document ids as keys and and arrays of
        event ids as values for certain filter criteria. The event array
        may be empty if there are no event criteria in the given filter.
        
        The filter is a combination of a document and an event filter. The
        document and the event criteria are joined with `and`.
        '''
        
        join = self.doc_table.outerjoin(
            self.deref_table,
            self.deref_table.c.laufnr == self.doc_table.c.hauptnr).outerjoin(
                self.event_table,
                self.event_table.c.ereignis_id == self.deref_table.c.ereignis_id)        
        query = select([self.doc_table.c.hauptnr, self.deref_table.c.ereignis_id]).\
            distinct().select_from(join)
        where_clauses = []
        
        event_where = self.event_filter_expression_builder.\
            create_filter_expression(document_event_reference_filter)
        if event_where is not None:
            where_clauses.append(event_where)
        document_where = self.doc_filter_expression_builder.\
            create_filter_expression(document_event_reference_filter)
        if document_where is not None:
            where_clauses.append(document_where)
        
        if where_clauses:
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

class DaoModule(Module):
    '''
    Injector module to bind the dao keys
    '''
    def configure(self, binder):
        binder.bind(baseinjectorkeys.CREATOR_PROVIDER_KEY,
                    ClassProvider(BasicCreatorProvider), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_FILTER_EXPRESSION_BUILDER_KEY,
                    ClassProvider(EventFilterExpressionBuilder), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILTER_EXPRESSION_BUILDER_KEY,
                    ClassProvider(DocumentFilterExpressionBuilder), scope=singleton)
        binder.bind(baseinjectorkeys.CREATOR_DAO_KEY,
                    ClassProvider(CreatorDao), scope=singleton)
        binder.bind(baseinjectorkeys.REGISTRY_DAO_KEY,
                    ClassProvider(RegistryDao), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY,
                    ClassProvider(DocumentTypeDao), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
                    ClassProvider(DocumentFileInfoDao), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_DAO_KEY,
                    ClassProvider(EventDao), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_DAO_KEY,
                    ClassProvider(DocumentDao), scope=singleton)
        binder.bind(baseinjectorkeys.RELATIONS_DAO_KEY,
                    ClassProvider(DocumentEventRelationsDao), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_TYPE_DAO_KEY,
                    ClassProvider(EventTypeDao), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_CROSS_REFERENCES_DAO_KEY,
                    ClassProvider(EventCrossreferencesDao), scope=singleton)

    @provider
    @singleton
    @inject
    def create_database_engine(self,
                               config_service:
                               baseinjectorkeys.CONFIG_KEY) -> baseinjectorkeys.DB_ENGINE_KEY:
        '''
        Creates the database engine from configuration information
        '''
        # pylint: disable=no-self-use
        arguments = {'echo': False}
        if config_service.dbname == ':memory:':
            # we want to be threadsafe when we are in the test environment
            arguments['connect_args'] = {'check_same_thread':False}
            arguments['poolclass'] = StaticPool
        return create_engine(config_service.connection_string, **arguments)
