'''
Created on 12.03.2016

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys


class CreatorService(object):
    '''
    Service to manage the creators in the database.
    '''

    @inject(creator_dao=baseinjectorkeys.CREATOR_DAO_KEY)
    def __init__(self, creator_dao):
        '''
        Uses the creator dao for database access
        '''
        self.creator_dao = creator_dao
        
    def find_all_active_creators(self):
        '''
        Returns all creators that have the visible flag set.
        '''
        return self.creator_dao.find_all_visible()
        