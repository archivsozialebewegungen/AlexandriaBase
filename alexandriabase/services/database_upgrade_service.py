'''
Created on 28.06.2016

@author: michael
'''
import sys
from injector import inject
from sqlalchemy.sql.expression import update, text, select
from alexandriabase import baseinjectorkeys
from alexandriabase.daos.metadata import REGISTRY_TABLE, CURRENT_VERSION

def get_version(connection):
    '''
    Reads the current database version from the registry table
    '''
    query = select([REGISTRY_TABLE])\
        .where(REGISTRY_TABLE.c.schluessel == 'version')  # @UndefinedVariable
    result = connection.execute(query)
    row = result.fetchone()
    return row[REGISTRY_TABLE.c.wert]  # @UndefinedVariable


class BaseUpdate():
    '''
    Baseclass for update classes that provides the set_version method
    '''
    
    def __init__(self, connection, dialect):
        self.connection = connection
        self.dialect = dialect
        
    def set_version(self, version):
        '''
        Updates the registry table to set the current version
        '''
        
        query = update(REGISTRY_TABLE)\
            .values(wert=version)\
            .where(REGISTRY_TABLE.c.schluessel == 'version')  # @UndefinedVariable
        self.connection.execute(query)

class UpdateFrom0_3(BaseUpdate):
    # pylint: disable=invalid-name
    '''
    Updates from version 0.3 to 0.4 (removes annoying not null constraints)
    '''
    
    dialect_specifics = {'sqlite': '',
                         'postgresql': 'alter table dokument alter seite drop not null, ' +
                                       'alter dateityp drop not null'}
    
    def __init__(self, connection, dialect):
        super().__init__(connection, dialect)
    
    def run(self):
        '''
        Runs the upgrade
        '''
        self.connection.execute(text(self.dialect_specifics[self.dialect]))
        self.set_version('0.4')

class DatabaseUpgradeService():
    '''
    Handles updating the database
    '''

    @inject(db_engine=baseinjectorkeys.DBEngineKey)
    def __init__(self, db_engine):
        '''
        Constructor
        '''
        self.db_engine = db_engine
        
    def is_update_necessary(self):
        '''
        Informs about necessity for an upgrade
        '''
        connection = self.db_engine.connect()
        db_version = get_version(connection)
        connection.close()
        return db_version != CURRENT_VERSION
    
    def run_update(self):
        '''
        Runs all unapplied upgrades in a transaction. Rolls back,
        if something goes wrong and throws received exception again.
        '''
        connection = self.db_engine.connect()
        transaction = connection.begin()
        try:
            db_version = get_version(connection)
            while db_version != CURRENT_VERSION:
                class_name = 'UpdateFrom' + db_version.replace('.', '_')
                updater_class = getattr(sys.modules[self.__module__], class_name)
                updater = updater_class(connection, self.db_engine.name)
                updater.run()
                db_version = get_version(connection)
        except Exception as exception:
            transaction.rollback()
            raise exception
        transaction.commit()
        connection.close()
