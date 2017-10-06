'''
Created on 11.10.2015

@author: michael
'''
from _functools import reduce
from threading import Lock
from sqlalchemy.sql.expression import or_, select, and_, delete
from sqlalchemy.sql.functions import func

from alexandriabase.base_exceptions import NoSuchEntityException, DataError
from alexandriabase.daos.metadata import get_foreign_keys


def combine_expressions(expressions, method):
    '''
    Combines the different expressions with and.
    '''
    if len(expressions) == 0:
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
                    searchterm_expressions.append(
                        func.upper(self.textcolumn).contains(searchterm.upper()))
        return searchterm_expressions


class GenericDao:
    '''
    Common functionality for all daos
    '''

    def __init__(self, db_engine):
        assert(db_engine != None)
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
        else:
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

    def get_by_id(self, entityid):
        ''' Get an entity by id. Throws exception when the entity does not exist.'''
        query = select([self.primary_key.table])\
            .where(self.primary_key == entityid)
        return self._get_exactly_one(query)

    def get_first(self, filter_expression=None):
        ''' Get the first entity or None if no entity exists or is allowed by filter.'''
        subquery = select([func.min(self.primary_key)])  # @UndefinedVariable
        if not isinstance(filter_expression, type(None)):
            subquery = subquery.where(filter_expression)
        query = select([self.primary_key.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        return self._get_one_or_none(query)

    def get_last(self, filter_expression=None):
        ''' Get the last entity or None if no entity exits or is allowed by filter.'''
        subquery = select([func.max(self.primary_key)])  # @UndefinedVariable
        if not isinstance(filter_expression, type(None)):
            subquery = subquery.where(filter_expression)
        query = select([self.primary_key.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        return self._get_one_or_none(query)

    def get_next(self, entity, filter_expression=None):
        ''' Get the next entity or the first, if it is the last'''
        where_clause = self.primary_key > entity.id  # @UndefinedVariable
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        subquery = select([func.min(self.primary_key)]).where(where_clause)  # @UndefinedVariable
        query = select([self.primary_key.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        entity = self._get_one_or_none(query)
        if not entity:
            return self.get_first(filter_expression)
        else:
            return entity

    def get_previous(self, entity, filter_expression=None):
        ''' Get the previous entity or the last, if it is the first'''
        where_clause = self.primary_key < entity.id  # @UndefinedVariable
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        subquery = select([func.max(self.primary_key)]).where(where_clause)  # @UndefinedVariable
        query = select([self.primary_key.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        entity = self._get_one_or_none(query)
        if not entity:
            return self.get_last(filter_expression)
        else:
            return entity

    def get_nearest(self, entity_id, filter_expression=None):
        ''' Get the entity matching the id, or, if not existing,
        the next entity after this id. If this does not provide
        an entity, get the last entity.'''
        where_clause = self.primary_key >= entity_id
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        subquery = select([func.min(self.primary_key)]).where(where_clause)
        query = select([self.table])\
            .where(self.primary_key == subquery)  # @UndefinedVariable
        entity = self._get_one_or_none(query)
        if not entity:
            return self.get_last(filter_expression)
        else:
            return entity

    def save(self, entity):
        '''
        Decides on the existence of the entity.id, if an update
        or an insert is necessary and executes the appropriate
        method in a transaction.
        '''
        if entity.id:
            return self.transactional(self._update, entity)
        else:
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
