'''
Created on 11.10.2015

@author: michael
'''
import unittest

from daotests.test_base import DatabaseBaseTest
from alexandriabase.daos import RegistryDao


class TestRegistryDao(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        self.dao = RegistryDao(self.engine)

    def tearDown(self):
        super().tearDown()

    def test_get(self):
        
        self.assertEqual("0.3", self.dao.get('version'))
        
    def test_get_non_existing_key(self):
        
        self.assertEqual(None, self.dao.get('not_existing'))

    def test_update(self):
        self.dao.set('version', '0.4')
        self.assertEqual("0.4", self.dao.get('version'))

    def test_insert(self):
        self.dao.set('not_existing', '0.4')
        self.assertEqual("0.4", self.dao.get('not_existing'))

if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
