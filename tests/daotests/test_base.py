'''
Created on 11.10.2015

@author: michael
'''
from injector import Injector
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import text
import unittest

from alexandriabase import AlexBaseModule, baseinjectorkeys
from alex_test_utils import setup_database_schema, load_table_data, clear_table_data, \
    TestEnvironment, MODE_SIMPLE
from alexandriabase.base_exceptions import NoSuchEntityException, DataError
from alexandriabase.daos import DaoModule, EntityDao,\
    EVENT_CROSS_REFERENCES_TABLE, EVENT_TABLE, CreatorDao
from alexandriabase.domain import Entity


tables = ("erfasser", "ereignistyp", "doktyp", "chrono", "dokument", "dverweis",  
          "everweis", "qverweis", "registry")


class TestUnimplementedMethods(unittest.TestCase):
    
    def test_non_entity_table(self):
        
        exception_raised = False
        try:
            EntityDao(None, EVENT_CROSS_REFERENCES_TABLE)
        except DataError:
            exception_raised = True
        self.assertTrue(exception_raised)

    def test_generic_dao_row_to_entity(self):
        
        dao = EntityDao(None, EVENT_TABLE)
        exception_raised = False
        row = {}
        try:
            dao._row_to_entity(row)
        except Exception:
            exception_raised = True
        self.assertTrue(exception_raised)
        
    def test_generic_dao_insert(self):
        
        dao = EntityDao(None, EVENT_TABLE)
        exception_raised = False
        try:
            dao._insert(Entity())
        except Exception:
            exception_raised = True
        self.assertTrue(exception_raised)

    def test_generic_dao_update(self):
        
        dao = EntityDao(None, EVENT_TABLE)
        exception_raised = False
        try:
            dao._update(Entity())
        except Exception:
            exception_raised = True
        self.assertTrue(exception_raised)

class TestDaoModuleConfiguration(unittest.TestCase):
    
    def setUp(self):
        self.env = TestEnvironment(mode=MODE_SIMPLE)

    def tearDown(self):
        self.env.cleanup()
            
    def test_configuration(self):
        
        injector = Injector([
                        AlexBaseModule(),
                        DaoModule()
                         ])

        # Try to get the database engine, which is the crucial part
        injector.get(baseinjectorkeys.DB_ENGINE_KEY)    
        
class DatabaseBaseTest(unittest.TestCase):

    def setUp(self):
        self.test_environment = TestEnvironment()
        self.injector = Injector([AlexBaseModule(), DaoModule()])
        self.engine = self.injector.get(baseinjectorkeys.DB_ENGINE_KEY)
        setup_database_schema(self.engine)
        load_table_data(tables, self.engine)

    def tearDown(self):
        clear_table_data(tables, self.engine)
        self.test_environment.cleanup()
        
class RollbackTest(DatabaseBaseTest):
    
    def setUp(self):
        DatabaseBaseTest.setUp(self)
        self.dao = CreatorDao(self.engine)

    def test_transaction_rollback(self):
        
        # Verify the erfasser table has an entry
        erfasser = self.dao.get_by_id(1)
        self.assertTrue(erfasser)
        
        exception_thrown = False
        try:
            self.dao.transactional(self._evil_function)
        except:
            exception_thrown = True
        self.assertTrue(exception_thrown)
        # Rollback should have happened, so the deletion of
        # all erfasser entries should have been reversed
        self.dao.clear_cache()
        erfasser = self.dao.get_by_id(1)
        self.assertTrue(erfasser)

        exception_thrown = False
        try:
            self._evil_function()
        except OperationalError:
            exception_thrown = True
        self.assertTrue(exception_thrown)
        # Now there should have been no rollback, all erfasser entries
        # should be gone
        self.dao.clear_cache()
        exception_thrown = False
        try:
            erfasser = self.dao.get_by_id(1)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown)
        
    def test_nested_transactions(self):
        
        self.transactional_function_ii()
        self.dao.clear_cache()
        creator = self.dao.get_by_id(1)
        self.assertEqual("MAX MUSTERMANN", creator.name)    
            
    def transactional_function(self):
        
        self.dao.transactional(self.function)
        
    def function(self):
        
        self.dao.connection.execute(text("DELETE FROM erfasser"))        
            
    def transactional_function_ii(self):
        
        self.dao.transactional(self.function_ii)
        
    def function_ii(self):
        self.transactional_function()
        self.dao.connection.execute(text("INSERT INTO erfasser (id, name, anzeige) VALUES (1, 'MAX MUSTERMANN', 1)"))        

    def _evil_function(self):
        
        self.dao.connection.execute(text("DELETE FROM erfasser"))
        self.dao.connection.execute(text("DELETE FROM nonexistingtable"))

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
