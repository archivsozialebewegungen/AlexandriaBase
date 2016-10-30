'''
This package provides daos and services for the
alexandria family of applications.
'''
import gettext
import os
import sys
from injector import Module, ClassProvider, singleton, provides, inject

from alexandriabase import baseinjectorkeys
from alexandriabase.config import Config


def get_locale_dir():
    '''
    Determines the location of the locale directory using
    the information of the location of the current module.
    '''
        
    this_module = get_locale_dir.__module__
    this_file = os.path.abspath(sys.modules[this_module].__file__)
    this_directory = os.path.dirname(this_file)
    return os.path.join(this_directory, 'locale')

def get_font_dir():
    '''
    Determines the location of the locale directory using
    the information of the location of the current module.
    '''
        
    this_module = get_font_dir.__module__
    this_file = os.path.abspath(sys.modules[this_module].__file__)
    this_directory = os.path.dirname(this_file)
    return os.path.join(this_directory, 'fonts')

gettext.install('alexandriabase', get_locale_dir())

class AlexBaseModule(Module):
    '''
    Injector module to bind the dao keys
    '''
    
    def __init__(self):
        self.config = None
    
    def configure(self, binder):
        pass
        

    @singleton
    @provides(baseinjectorkeys.CONFIG_KEY)
    @inject(config_file=baseinjectorkeys.CONFIG_FILE_KEY)
    def get_config(self, config_file):
        '''
        Returns the configuration.
        
        The explicit singleton code here is for using
        the config before the injector is initialized
        because we want to keep injection information
        in the config. Otherwise the annotation would
        suffice.
        '''
        if self.config is None:
            self.config = Config(config_file)
        return self.config
