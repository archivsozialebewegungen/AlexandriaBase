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

moduledir = os.path.abspath(os.path.dirname(__file__))
localedir = os.path.join(moduledir, 'locale')
fontdir = os.path.join(moduledir, 'fonts')

translate = gettext.translation('handroll', localedir, fallback=True)
_ = translate.gettext

class AlexBaseModule(Module):
    '''
    Injector module to bind the dao keys
    '''
    
    def __init__(self):
        self.config = None
    
    @singleton
    @provider
    def get_config(self) -> Config:
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
