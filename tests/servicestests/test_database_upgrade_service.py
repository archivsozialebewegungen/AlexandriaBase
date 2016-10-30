'''
Created on 28.06.2016

@author: michael
'''
import unittest
from alexandriabase.services.database_upgrade_service import DatabaseUpgradeService
from daotests.test_base import DatabaseBaseTest

from alexandriabase.daos.registry_dao import RegistryDao


class DatabaseUpgradeServiceTest(DatabaseBaseTest):


    def setUp(self):
        super().setUp()
        self.upgrade_service = DatabaseUpgradeService(self.engine)


    def tearDown(self):
        super().tearDown()


    def testUpgrade(self):
        self.assertTrue(self.upgrade_service.is_update_necessary())
        self.upgrade_service.run_update()
        self.assertFalse(self.upgrade_service.is_update_necessary())

    def testFailingUpgrade(self):
        registry_dao = RegistryDao(self.engine)
        registry_dao.set('version', 'not_existing')
        self.assertTrue(self.upgrade_service.is_update_necessary())
        expected_exception = False
        try:
            self.upgrade_service.run_update()
        except Exception:
            expected_exception = True
        self.assertTrue(expected_exception)
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()