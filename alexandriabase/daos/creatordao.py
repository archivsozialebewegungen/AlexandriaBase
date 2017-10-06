'''
Created on 11.10.2015

@author: michael
'''
from injector import inject
from sqlalchemy.sql.expression import select, insert, update

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.basedao import CachingDao
from alexandriabase.daos.metadata import CREATOR_TABLE
from alexandriabase.domain import Creator


class CreatorDao(CachingDao):
    '''
    Reads users from the database
    '''

    @inject
    def __init__(self, db_engine: baseinjectorkeys.DB_ENGINE_KEY):
        super().__init__(db_engine, CREATOR_TABLE)
        self.cache = {}



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

    def _update(self, creator):
        query = update(self.table)\
            .values(name=creator.name,
                    anzeige=creator.visible)\
            .where(self.table.c.id == creator.id)
        self.connection.execute(query)
        return creator

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
