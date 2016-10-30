'''
Created on 18.10.2015

@author: michael
'''
from math import ceil
from alexandriabase.domain import PaginatedResult

class BaseRecordService():
    '''
    classdocs
    '''
    def __init__(self, dao, filter_expression_builder):
        '''
        The constructor expects the dao for the record type
        as parameter and a dao specific filter expression builder.
        '''
        self.dao = dao
        self.filter_expression_builder = filter_expression_builder
    
    def get_by_id(self, object_id):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_by_id(object_id)
        
    def get_first(self, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_first(filter_expression)
    
    def get_next(self, entity, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_next(entity, filter_expression)
    
    def get_previous(self, entity, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_previous(entity, filter_expression)
    
    def get_last(self, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_last(filter_expression)
    
    def get_nearest(self, entity_id, filter_expression):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.get_nearest(entity_id, filter_expression)
    
    def create_filter_expression(self, filter_object):
        '''
        Uses a dao specific filter object to build a filter expression
        '''
        return self.filter_expression_builder.create_filter_expression(filter_object)
    
    def save(self, entity):
        '''
        Just reaches through to the dao.
        '''
        return self.dao.save(entity)

    def delete(self, entity):
        '''
        Just reaches through to the dao.
        '''
        self.dao.delete(entity.id)

    def find(self, condition, page, page_size):
        '''
        Finds documents and wraps them with a PaginatedResult
        '''
        
        result = PaginatedResult()
        result.page = page
        result.page_size = page_size
        number_of_entities = self.dao.get_count(condition)
        result.number_of_pages = ceil((number_of_entities * 1.0) / page_size)
        result.entities = self.dao.find(condition, page, page_size)
        return result
