'''
Created on 05.11.2015

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys
from alexandriabase.domain import Creator


class BasicCreatorProvider(object):
    '''
    This basic implementation of a creator provider
    always return the admin as creator. This is a
    creator provider for automated scripts etc. Interactive
    applications should provide their own implementations
    that return the current user.
    '''
    @inject
    def __init__(self, creator_dao: baseinjectorkeys.CREATOR_DAO_KEY):
        self.creator_dao = creator_dao

    def _get_creator(self):
        ''' Private getter to use in property.'''
        creator = self.creator_dao.find_by_name("Admin")
        if creator is None:
            creator = Creator()
            creator.name = "Admin"
            creator.visible = False
            creator = self.creator_dao.save(creator)
        return creator

    creator = property(_get_creator)
