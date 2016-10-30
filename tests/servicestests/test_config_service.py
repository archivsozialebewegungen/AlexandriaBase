'''
Created on 18.10.2015

@author: michael
'''
import os
import unittest

from alex_test_utils import get_testfiles_dir, TestEnvironment
from alexandriabase.config import Config, NoSuchConfigValue


class ConfigTests(unittest.TestCase):


    def setUp(self):
        config_file = os.path.join(get_testfiles_dir(), "testconfig.xml")
        self.config = Config(config_file)

    def test_reading_simple(self):
        self.assertEqual("sqlite:///:memory:", self.config.connection_string)
        
    def test_reading_List(self):
        self.assertEqual([], self.config.archive_dirs)

    def test_writing_list(self):
        self.config.archive_dirs = ['archivedir']
        self.assertEqual(['archivedir'], self.config.archive_dirs)

    def testNotExistingValue(self):
        exception_raised = False
        try:
            self.config._get_string_value("no_such_key")
        except NoSuchConfigValue:
            exception_raised = True
        self.assertTrue(exception_raised)

    def testNotExistingValueForLists(self):
        exception_raised = False
        try:
            self.config._get_list_value("no_such_key")
        except NoSuchConfigValue:
            exception_raised = True
        self.assertTrue(exception_raised)
        
    def testNotExistingValueForMaps(self):
        exception_raised = False
        try:
            self.config._get_map_value("no_such_key")
        except NoSuchConfigValue:
            exception_raised = True
        self.assertTrue(exception_raised)

    def testConfigWithErrors(self):
        config_file = os.path.join(get_testfiles_dir(), "testconfig_witherrors.xml")
        exception_raised = False
        try:
            self.config = Config(config_file)
        except Exception as e:
            exception_raised = True
            self.assertEqual("Configuration needs exactly 1 configuration node", e.args[0])
        self.assertTrue(exception_raised)
        
    def test_rewrite(self):
        env = TestEnvironment()
        config = env.config
        config.dbengine = "postgres"
        config.dbuser = 'michael'
        config.dbpassword = 'pwd'
        config.dbport = '1234'
        config.dbname = 'archiv'
        config.dbhost = 'localhost'

        config.archive_dirs = ['archivedir']
        config.filetypealiases = {'blue': 'tif', 'green': 'jpg', 'yellow': 'mpg'}
        
        config.write_config()
        
        new_config = Config(env.config_file_name)
        self.assertEqual('postgres://michael:pwd@localhost:1234/archiv', new_config.connection_string)
        self.assertEqual(['archivedir'], new_config.archive_dirs)
        self.assertEqual('jpg', new_config.filetypealiases['green'])
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'ConfigTests.testName']
    unittest.main()