'''
Persistence module that handles all database access
'''
from injector import Module, ClassProvider, singleton, provider, inject
from sqlalchemy.engine import create_engine
from sqlalchemy.pool import StaticPool

from alexandriabase import baseinjectorkeys
from alexandriabase.daos.creatordao import CreatorDao
from alexandriabase.daos.documentdao import DocumentDao, \
    DocumentFilterExpressionBuilder
from alexandriabase.daos.documentfileinfodao import DocumentFileInfoDao
from alexandriabase.daos.documenttypedao import DocumentTypeDao
from alexandriabase.daos.eventcrossreferencesdao import EventCrossreferencesDao
from alexandriabase.daos.eventdao import EventDao, \
    EventFilterExpressionBuilder
from alexandriabase.daos.eventtypedao import EventTypeDao
from alexandriabase.daos.relationsdao import DocumentEventRelationsDao
from alexandriabase.daos.registry_dao import RegistryDao


class DaoModule(Module):
    '''
    Injector module to bind the dao keys
    '''
    def configure(self, binder):
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
