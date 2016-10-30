'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, insert, update

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.metadata import REGISTRY_TABLE
from alexandriabase.daos.basedao import GenericDao


class RegistryDao(GenericDao):
    '''
    Reads and writes keys / value pairs from the database
    '''

    @inject(db_engine=baseinjectorkeys.DBEngineKey)
    def __init__(self, db_engine):
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
