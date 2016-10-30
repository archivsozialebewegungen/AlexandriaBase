'''
Created on 31.01.2016

@author: michael
'''
import os
from PIL import Image  # @UnresolvedImport
from injector import inject

from alexandriabase import baseinjectorkeys
import logging
import math


def get_graphic_file_resolution(file):
    '''
    Gets the resolution from the info property of a PIL image
    '''
    image = Image.open(file)
    file_info = image.info
    if not 'dpi' in file_info:
        return None
    x_res = file_info['dpi'][0]
    y_res = file_info['dpi'][1]
    # Might be a problem with floats
    if abs(x_res - y_res) >= 0.001:
        logger = logging.getLogger()
        logger.debug("Difference is %f." % abs(x_res - y_res))
        raise DifferentXAndYResolutions(x_res, y_res)
    return x_res

def get_gif_file_resolution(file):
    # pylint: disable=unused-argument
    '''
    Gifs always have a resolution of 72 dpi. In the early days of
    the first alexandria implementation we scanned with 300 dpi
    and converted it straight to a gif file. So in fact our gifs
    have 300 dpi 
    '''
    return 300

class UnsupportedFileFormat(Exception):
    '''
    Raised when the given file format is not
    supported.
    
    Argument:
        format The offending format
    '''
    def __init__(self, file_format):
        # pylint: disable=super-init-not-called
        self.file_format = file_format
        
class UnsupportedFileResolution(Exception):
    '''
    Raised, when the fileformat is supported,
    but not with this resolution.
    '''
    def __init__(self, file_format, resolution):
        # pylint: disable=super-init-not-called
        self.file_format = file_format
        self.x_resolution = resolution
        self.y_resolution = resolution
        
class DifferentXAndYResolutions(UnsupportedFileResolution):
    '''
    Raised, when the x resolutions does not match the
    y resolution.
    '''
    
    def __init__(self, x_resolution, y_resolution):
        # pylint: disable=super-init-not-called
        self.file_format = None
        self.x_resolution = x_resolution
        self.y_resolution = y_resolution

class FileFormatService:
    '''
    Check service for file types.
    
    Checks if the file type is supported, and when it is an
    image file, determines the resolution and checks if it is
    allowed. 
    
    The service may be configured overwriting the properties
    supported_formats, format_aliases, resolution_handlers and
    allowed resolutions 
    '''
    @inject(config=baseinjectorkeys.CONFIG_KEY)
    def __init__(self, config):
        self.supported_formats = config.filetypes
        self.format_aliases = config.filetypealiases
        
        # TODO: Also put these options into the configuration
        self.resolution_handlers = {'tif': get_graphic_file_resolution,
                                    'jpg': get_graphic_file_resolution,
                                    'png': get_graphic_file_resolution,
                                    'gif': get_gif_file_resolution}
        self.allowed_resolutions = {'tif': [300, 400]}

    def get_format_and_resolution(self, file):
        '''
        Determines the file format and, if it
        is a graphics format, the resolution.
        '''
        fileformat = self._get_file_format(file)
        resolution = self._get_file_resolution(file, fileformat)
        return fileformat, resolution
    
    def _get_file_format(self, file):
        '''
        Determines the format and checks if it is supported.
        If not, an UnsupportedFileFormat exception is raised.
        '''
        # pylint: disable=unused-variable
        filename, file_extension = os.path.splitext(file) # @UnusedVariable
        fileformat = file_extension[1:].lower()
        if fileformat in self.format_aliases:
            fileformat = self.format_aliases[fileformat]
        if not fileformat in self.supported_formats:
            raise UnsupportedFileFormat(fileformat)
        return fileformat
    
    def _get_file_resolution(self, file, fileformat):
        '''
        Determines the file resolution (if appropriate). Raises
        an UnsupportedFileResolution exception, if it violates
        the configured constraints.
        '''
        resolution = None
        if fileformat in self.resolution_handlers:
            resolution = self.resolution_handlers[fileformat](file)
        if fileformat in self.allowed_resolutions:
            if not resolution in self.allowed_resolutions[fileformat]:
                raise UnsupportedFileResolution(fileformat, resolution)
        return resolution
