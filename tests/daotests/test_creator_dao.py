'''
Created on 11.10.2015

@author: michael
'''
import unittest

from alexandriabase.base_exceptions import NoSuchEntityException
from alexandriabase.daos.creatordao import CreatorDao
from alexandriabase.domain import Creator
from daotests.test_base import DatabaseBaseTest


class TestCreatorDao(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        self.dao = CreatorDao(self.engine)
        self.dao.clear_cache()

    def tearDown(self):
        self.dao.clear_cache()
        super().tearDown()

    def test_find_by_id(self):
        
        self.assertEqual(len(self.dao.cache), 0)
        erfasser = self.dao.get_by_id(1)
        self.assertEqual(erfasser.name, "Max Mustermann")
        self.assertEqual(self.dao.cache[1], erfasser)
        exception_thrown = False
        try:
            erfasser = self.dao.get_by_id(666)
        except NoSuchEntityException:
            exception_thrown = True
        self.assertTrue(exception_thrown)
        

    def test_cache_usage(self):
        
        dummy = Creator(7)
        dummy.name = "Ingrid Schulz"
        self.dao.cache[dummy.id] = dummy

        erfasser = self.dao.get_by_id(7)
        self.assertEqual(erfasser.name, "Ingrid Schulz")
        
    def test_find_by_nameI(self):
        creator = self.dao.find_by_name("Erna Musterfrau")
        self.assertTrue(creator != None, "Creator not found")
        self.assertEqual(creator.id, 2)
        self.assertEqual(creator.name, "Erna Musterfrau")
        self.assertFalse(creator.visible)
        
    def test_find_by_nameII(self):
        # Edge case. Should not throw exception
        creator = self.dao.find_by_name("Nicht existierender Name")
        self.assertTrue(creator == None)

    def test_find_by_name_with_cache_working(self):
        self.dao.find() # preloads cache
        creator = self.dao.find_by_name("Max Mustermann")
        self.assertEqual(creator.id, 1)

    def test_find_by_name_with_cache_failing(self):
        self.dao.find()
        creator = self.dao.find_by_name("Nicht existierender Name")
        self.assertTrue(creator == None)

    def test_save_new(self):
        number_of_creators = len(self.dao.find())

        creator = Creator()
        creator.name = 'Ingrid Schulz'
        creator.visible = False
        creator = self.dao.save(creator)
        
        self._check_entity(creator.id)

        self.assertEqual(len(self.dao.find()), number_of_creators + 1)
        
    def test_update(self):
        number_of_creators = len(self.dao.find())
        
        creator = self.dao.get_by_id(1)
        creator.name = 'Ingrid Schulz'
        creator.visible = False
        
        creator = self.dao.save(creator)

        self._check_entity(creator.id)
        
        # Check that there is no additional creator
        self.assertEqual(len(self.dao.find()), number_of_creators)

    def test_get_nearest(self):
        '''
        This test does not make a lot of sense (why would someone get the
        nearest creator), but it checks the base functionality, so it is
        incorporated here.
        '''
        
        creator = self.dao.get_nearest(0, None)
        self.assertEqual(1, creator.id)
        creator = self.dao.get_nearest(1, None)
        self.assertEqual(1, creator.id)
        creator = self.dao.get_nearest(7, None)
        self.assertEqual(2, creator.id)
        filter_expression = self.dao.table.c.id > 1
        creator = self.dao.get_nearest(0, filter_expression)
        self.assertEqual(2, creator.id)

    def _check_entity(self, creator_id):
        # Check that cached version is up to date
        creator = self.dao.get_by_id(creator_id)
        self.assertEqual(creator.id, creator_id)
        self.assertEqual(creator.name, 'Ingrid Schulz')
        self.assertFalse(creator.visible)
        
        # Check that stored version is up to date
        self.dao.clear_cache()
        creator = self.dao.get_by_id(creator_id)
        self.assertEqual(creator.id, creator_id)
        self.assertEqual(creator.name, 'Ingrid Schulz')
        self.assertFalse(creator.visible)
        
    def test_find_all_visible(self):
        
        visible_list = self.dao.find_all_visible()
        self.assertEqual(1, len(visible_list))
        self.assertEqual("Max Mustermann", visible_list[0].name)
if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
