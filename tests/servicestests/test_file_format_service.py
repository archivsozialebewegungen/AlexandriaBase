'''
Created on 30.01.2016

@author: michael
'''
import os
import unittest

from alex_test_utils import get_testfiles_dir, TestEnvironment
from alexandriabase.services import FileFormatService, \
    UnsupportedFileResolution, get_graphic_file_resolution, \
    UnsupportedFileFormat


class FileFormatServiceTest(unittest.TestCase):

    def setUp(self):
        env = TestEnvironment()
        self.service = FileFormatService(env.config)

    def test_tif_file_unsupported_resolution(self):
        
        file = os.path.join(get_testfiles_dir(), "testfile.tif")
        exception_raised = False
        try:
            self.service.get_format_and_resolution(file)
        except UnsupportedFileResolution as e:
            self.assertEqual(e.x_resolution, 72)
            exception_raised = True
        self.assertTrue(exception_raised)
            
    def test_tif_file_bad_resolution(self):
        
        file = os.path.join(get_testfiles_dir(), "testfile_bad_resolution.tif")
        exception_raised = False
        try:
            self.service.get_format_and_resolution(file)
        except UnsupportedFileResolution as e:
            self.assertEqual(144, e.x_resolution)
            self.assertEqual(72, e.y_resolution)
            exception_raised = True
        self.assertTrue(exception_raised)

    def test_tif_file_supported_resolution(self):
        
        self.service.allowed_resolutions['tif'] = [72, 300, 400]
        
        file = os.path.join(get_testfiles_dir(), "testfile.tif")
        file_format, res = self.service.get_format_and_resolution(file)
        self.assertEqual('tif', file_format)
        self.assertEqual(72, res)
            
    def test_gif_file(self):
                
        file = os.path.join(get_testfiles_dir(), "testfile.gif")
        file_format, res = self.service.get_format_and_resolution(file)
        self.assertEqual('gif', file_format)
        self.assertEqual(300, res)
        
    def test_unsupported_format_file(self):
        self.service.supported_formats = ['tif', 'jpg']
        file = os.path.join(get_testfiles_dir(), "testfile.gif")
        exception_raised = False
        try:
            self.service.get_format_and_resolution(file)
        except UnsupportedFileFormat as e:
            self.assertEqual('gif', e.file_format)
            exception_raised = True
        self.assertTrue(exception_raised)
    
    def test_file_format_aliases(self):
        
        self.service.supported_formats = ['tiff']
        self.service.format_aliases = {'tif': 'tiff'}
        self.service.resolution_handlers = {'tiff': get_graphic_file_resolution}

        file = os.path.join(get_testfiles_dir(), "testfile.tif")
        file_format, res = self.service.get_format_and_resolution(file)
        self.assertEqual('tiff', file_format)
        self.assertEqual(72, res)

    def test_jpeg_file(self):
        file = os.path.join(get_testfiles_dir(), "testfile.jpg")
        file_format, res = self.service.get_format_and_resolution(file)
        self.assertEqual('jpg', file_format)
        self.assertEqual(400, res)

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()