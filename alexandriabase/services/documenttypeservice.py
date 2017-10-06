'''
Created on 01.04.2016

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys


class DocumentTypeService(object):
    '''
    classdocs
    '''

    @inject
    def __init__(self, document_type_dao: baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY):
        '''
        Constructor
        '''
        self.document_type_dao = document_type_dao
        
    def get_document_type_dict(self):
        '''
        Returns all document types in form of a dictionary.
        '''
        type_dict = {}
        types = self.document_type_dao.get_all()
        for document_type in types:
            type_dict[document_type.description.upper()] = document_type
        return type_dict

    def get_document_types(self):
        '''
        Returns all document types as a dictionary with
        the document type id as key and the document type description
        as value.
        '''
        type_dict = {}
        types = self.document_type_dao.get_all()
        for document_type in types:
            type_dict[document_type.id] = document_type.description
        return type_dict
    
    def get_by_id(self, doc_type_id):
        '''
        Fetches a single document type by id.
        '''
        return self.document_type_dao.get_by_id(doc_type_id)
