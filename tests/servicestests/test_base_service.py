'''
Created on 19.10.2015

@author: michael
'''
from injector import Injector
import unittest
from unittest.mock import MagicMock

from alex_test_utils import TestEnvironment, MODE_SIMPLE, TestModule
from alexandriabase import baseinjectorkeys, AlexBaseModule
from alexandriabase.daos import DaoModule
from alexandriabase.domain import Entity
from alexandriabase.services import ServiceModule
from alexandriabase.services.baseservice import BaseRecordService


class TestDaoModuleConfiguration(unittest.TestCase):
    
    def setUp(self):
        self.env = TestEnvironment(mode=MODE_SIMPLE)

    def tearDown(self):
        self.env.cleanup()
            
    def test_configuration(self):
        
        injector = Injector([
                        TestModule(self.env),
                        AlexBaseModule(),
                        DaoModule(),
                        ServiceModule
                         ])

        # Try to get the database engine, which is the crucial part
        injector.get(baseinjectorkeys.DBEngineKey)
        
        # Test getting pdf handlers
        injector.get(baseinjectorkeys.PDF_HANDLERS_KEY)

        # Test getting image generators
        injector.get(baseinjectorkeys.IMAGE_GENERATORS_KEY)

class Test(unittest.TestCase):


    def setUp(self):
        self.dao = MagicMock()
        self.filter_expression_builder = MagicMock()
        self.base_service = BaseRecordService(self.dao, self.filter_expression_builder)


    def testGetById(self):
        self.base_service.get_by_id(4711)
        self.dao.get_by_id.assert_called_with(4711)
        
    def testGetFirst(self):
        filter_expression = MagicMock()
        self.base_service.get_first(filter_expression)
        self.dao.get_first.assert_called_with(filter_expression)
        
    def testGetNext(self):
        filter_expression = MagicMock()
        entity = MagicMock()
        self.base_service.get_next(entity, filter_expression)
        self.dao.get_next.assert_called_with(entity, filter_expression)
        
    def testGetLast(self):
        filter_expression = MagicMock()
        self.base_service.get_last(filter_expression)
        self.dao.get_last.assert_called_with(filter_expression)
        
    def testGetPrevious(self):
        filter_expression = MagicMock()
        entity = MagicMock()
        self.base_service.get_previous(entity, filter_expression)
        self.dao.get_previous.assert_called_with(entity, filter_expression)
        
    def testGetFilterExpression(self):
        filter_object = MagicMock()
        self.base_service.create_filter_expression(filter_object)
        self.filter_expression_builder.create_filter_expression.assert_called_with(filter_object)
        
    def testSave(self):
        entity = MagicMock()
        self.base_service.save(entity)
        self.dao.save.assert_called_once_with(entity)

    def test_delete(self):
        entity = Entity(4711)
        self.base_service.delete(entity)
        self.dao.delete.assert_called_once_with(4711)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()