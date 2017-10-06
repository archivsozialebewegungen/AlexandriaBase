'''
Created on 11.10.2015

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import CachingDao
from alexandriabase.daos.metadata import DOCUMENT_TYPE_TABLE
from alexandriabase.domain import DocumentType


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
