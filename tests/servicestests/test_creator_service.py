'''
Created on 12.03.2016

@author: michael
'''
import unittest
from unittest.mock import MagicMock

from alexandriabase.daos import CreatorDao
from alexandriabase.domain import Creator
from alexandriabase.services import CreatorService


class CreatorServiceTest(unittest.TestCase):


    def testFindVisible(self):
        dao = MagicMock(spec=CreatorDao)
        dao.find_all_visible.return_value = [Creator(34), Creator(35)]
        service = CreatorService(dao)
        result = service.find_all_active_creators()
        self.assertEqual(35, result[1].id)
        dao.find_all_visible.assert_called_once_with()
        
        


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()