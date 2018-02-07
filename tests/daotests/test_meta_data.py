'''
Created on 26.11.2015

@author: michael
'''
import unittest
from alexandriabase.daos import get_foreign_keys, EVENT_TABLE,\
    EVENT_EVENTTYPE_REFERENCE_TABLE, EVENT_CROSS_REFERENCES_TABLE,\
    DOCUMENT_EVENT_REFERENCE_TABLE

class MetaDataTests(unittest.TestCase):


    def testForeignKeys(self):
        keys = get_foreign_keys(EVENT_TABLE.c.ereignis_id)  # @UndefinedVariable
        self.assertEqual(len(keys), 4)
        self.assertIn(EVENT_EVENTTYPE_REFERENCE_TABLE.c.ereignis_id, keys)  # @UndefinedVariable
        self.assertIn(EVENT_CROSS_REFERENCES_TABLE.c.id1, keys)  # @UndefinedVariable
        self.assertIn(EVENT_CROSS_REFERENCES_TABLE.c.id2, keys)  # @UndefinedVariable
        self.assertIn(DOCUMENT_EVENT_REFERENCE_TABLE.c.ereignis_id, keys)  # @UndefinedVariable


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()