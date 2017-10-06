'''
This package provider daos and services for the
alexandria family of applications.
'''
import gettext
import os
import sys
from injector import Module, ClassProvider, singleton, provider, inject

from alexandriabase import baseinjectorkeys as injectorkeys
from alexandriabase.config import Config

def get_this_directory():

    this_module = get_locale_dir.__module__
    this_file = os.path.abspath(sys.modules[this_module].__file__)
    return os.path.dirname(this_file)

def get_locale_dir():
    '''
    Determines the location of the locale directory using
    the information of the location of the current module.
    '''
        
    return os.path.join(get_this_directory(), 'locale')

gettext.install('alexandriabase', get_locale_dir())

def get_font_dir():
    '''
    Determines the location of the font directory using
    the information of the location of the current module.
    '''
        
    return os.path.join(get_this_directory(), 'fonts')

# Must be done after installing gettext
from alexandriabase.daos.basiccreatorprovider import BasicCreatorProvider

class AlexBaseModule(Module):
    '''
    Injector module to bind the dao keys
    '''
    
    def __init__(self):
        self.config = None
    
    def configure(self, binder):
        binder.bind(injectorkeys.CREATOR_PROVIDER_KEY,
                    ClassProvider(BasicCreatorProvider),
                    scope=singleton)
        

    @singleton
    @provider
    def get_config(self) -> injectorkeys.CONFIG_KEY:
        '''
        Returns the configuration.
        
        The explicit singleton code here is for using
        the config before the injector is initialized
        because we want to keep injection information
        in the config. Otherwise the annotation would
        suffice.
        '''
        if self.config is None:
            self.config = Config()
        return self.config
