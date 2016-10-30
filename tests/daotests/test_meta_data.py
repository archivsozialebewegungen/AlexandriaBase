'''
Created on 26.11.2015

@author: michael
'''
import unittest

import alexandriabase.daos.metadata as metadata


class MetaDataTests(unittest.TestCase):


    def testForeignKeys(self):
        keys = metadata.get_foreign_keys(metadata.EVENT_TABLE.c.ereignis_id)  # @UndefinedVariable
        self.assertEqual(len(keys), 4)
        self.assertIn(metadata.EVENT_EVENTTYPE_REFERENCE_TABLE.c.ereignis_id, keys)  # @UndefinedVariable
        self.assertIn(metadata.EVENT_CROSS_REFERENCES_TABLE.c.id1, keys)  # @UndefinedVariable
        self.assertIn(metadata.EVENT_CROSS_REFERENCES_TABLE.c.id2, keys)  # @UndefinedVariable
        self.assertIn(metadata.DOCUMENT_EVENT_REFERENCE_TABLE.c.ereignis_id, keys)  # @UndefinedVariable


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()