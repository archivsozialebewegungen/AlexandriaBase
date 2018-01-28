'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, and_, delete, update, insert, or_
from sqlalchemy.sql.functions import func

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import GenericFilterExpressionBuilder, EntityDao
from alexandriabase.daos.metadata import DOCUMENT_TABLE
from alexandriabase.domain import Document, DocumentStatistics


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
        self._append_expression(self._build_location_expression(document_filter))
        self._append_expression(self._build_filetype_expression(document_filter))
        self._append_expression(self._build_document_type_expression(document_filter))

    def _build_location_expression(self, document_filter):
        '''
        Creates a location expression.
        '''
        if not document_filter.location:
            return None
        location = document_filter.location.upper()
        return or_(self.table.c.standort == location,
                   self.table.c.standort.startswith("%s." % location))

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
        return self.table.c.hauptnr.in_(subquery)

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
        self.config = config
        self.creator_dao = creator_dao
        self.document_type_dao = document_type_dao
        self.creator_provider = creator_provider

    def get_first(self, filter_expression=None):
        subquery = select([func.min(self.table.c.hauptnr)])
        if not isinstance(filter_expression, type(None)):
            subquery = subquery.where(filter_expression)
        query = self._generate_query_from_subquery(subquery)
        return self._get_one_or_none(query)

    def get_last(self, filter_expression=None):
        subquery = select([func.max(self.table.c.hauptnr)])
        if not isinstance(filter_expression, type(None)):
            subquery = subquery.where(filter_expression)
        query = self._generate_query_from_subquery(subquery)
        return self._get_one_or_none(query)

    # pylint: disable=arguments-differ
    def get_next(self, dokument, filter_expression=None):
        where_clause = DOCUMENT_TABLE.c.hauptnr > dokument.id  # @UndefinedVariable
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        function = func.min(self.table.c.hauptnr)
        subquery = select([function]).where(where_clause)
        query = self._generate_query_from_subquery(subquery)
        document = self._get_one_or_none(query)
        if document is None:
            return self.get_first(filter_expression)
        return document

    def get_previous(self, dokument, filter_expression=None):
        where_clause = self.table.c.hauptnr < dokument.id
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        function = func.max(self.table.c.hauptnr)
        subquery = select([function]).where(where_clause)
        return self._get_one_or_last(subquery, filter_expression)
        
    def get_nearest(self, entity_id, filter_expression=None):
        where_clause = self.table.c.hauptnr >= entity_id
        if not isinstance(filter_expression, type(None)):
            where_clause = and_(filter_expression, where_clause)
        subquery = select([func.min(self.table.c.hauptnr)]).where(where_clause)
        return self._get_one_or_last(subquery, filter_expression)
        
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
