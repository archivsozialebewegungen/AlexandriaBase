'''
Created on 02.12.2015

@author: michael
'''

class NoSuchEntityException(Exception):
    '''
    Exception raised when an entity searched for does not exist.
    '''
    
    def __init__(self, message):
        super().__init__()
        self.message = message
        
class DataError(Exception):
    '''
    Exception raised on inconistencies in the database.
    '''
    def __init__(self, message):
        super().__init__()
        self.message = message
