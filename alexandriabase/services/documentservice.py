'''
Created on 18.10.2015

@author: michael
'''
from injector import inject

from alexandriabase import baseinjectorkeys
from alexandriabase.domain import Document
from alexandriabase.services.baseservice import BaseRecordService
from alexandriabase.services.documentfilemanager import DocumentFileNotFound
from alexandriabase.services.fileformatservice import get_gif_file_resolution,\
    get_graphic_file_resolution

class DocumentService(BaseRecordService):
    '''
    Service to bundle the complicated document file management
    with the database information
    '''

    @inject
    def __init__(self,
                 dokument_dao: baseinjectorkeys.DOCUMENT_DAO_KEY,
                 document_file_info_dao: baseinjectorkeys.DOCUMENT_FILE_INFO_DAO_KEY,
                 document_file_manager: baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                 document_type_dao: baseinjectorkeys.DOCUMENT_TYPE_DAO_KEY,
                 document_file_provider: baseinjectorkeys.DOCUMENT_FILE_PROVIDER,
                 ereignis_dao: baseinjectorkeys.EVENT_DAO_KEY,
                 file_format_service: baseinjectorkeys.FILE_FORMAT_SERVICE,
                 filter_expression_builder:
                 baseinjectorkeys.DOCUMENT_FILTER_EXPRESSION_BUILDER_KEY):
        # pylint: disable=too-many-arguments
        BaseRecordService.__init__(self, dokument_dao, filter_expression_builder)
        self.document_file_info_dao = document_file_info_dao
        self.document_file_manager = document_file_manager
        self.document_type_dao = document_type_dao
        self.document_file_provider = document_file_provider
        self.ereignis_dao = ereignis_dao
        self.file_format_service = file_format_service
        
    def get_by_id(self, object_id):
        '''
        Just reaches through to the dao.
        '''
        file_info = self.document_file_info_dao.get_by_id(object_id)
        return self.dao.get_by_id(file_info.document_id)
                
    def add_document_file(self, document, file):
        '''
        Determines the file format (might result in an exception if the
        file format is not supported), then creates a new database entry
        for the file and finally moves the file to its correct location.
        '''
        
        file_format, resolution = self.file_format_service.get_format_and_resolution(file)
        file_info = self.document_file_info_dao.create_new_file_info(
            document.id,
            file_format,
            resolution)
        self._add_file_with_error_handling(file, file_info)
        
    def replace_document_file(self, file_info, file):
        '''
        Updates the format and resolution information in the database
        and moves the file to the place where it belongs. The existing
        file will be renamed to have .deleted as suffix. A former .deleted
        file will be overwritten.
        '''
        self.document_file_manager.delete_file(file_info)
        file_info.filetype, file_info.resolution = \
            self.file_format_service.get_format_and_resolution(file)
        self.document_file_info_dao.save(file_info)
        self._add_file_with_error_handling(file, file_info)

    def _add_file_with_error_handling(self, file, file_info):
        '''
        Helper method that tries to make as little mess as possible
        in the filesystem if something goes wrong.
        '''
        # pylint: disable=bare-except
        try:
            self.document_file_manager.add_file(file, file_info)
        except Exception as generic_exception:
            try:
                self.document_file_manager.delete_file(file_info)
            except:
                pass
            self.document_file_info_dao.delete(file_info.id)
            raise generic_exception

    def delete_file(self, document_file_info):
        '''
        Just deletes one document file (and the pertaining database information).
        The document entry itself remains.
        '''
        self.document_file_manager.delete_file(document_file_info)
        self.document_file_info_dao.delete(document_file_info.id)

    # pylint: disable=arguments-differ
    def delete(self, document):
        '''
        Deletes all the document files and all the database information
        '''
        file_infos = self.document_file_info_dao.get_file_infos_for_document(document.id)
        for file_info in file_infos:
            self.document_file_manager.delete_file(file_info)
        self.dao.delete(document.id)

    def get_file_infos_for_document(self, document):
        '''
        Returns all the file infos for the given document (what else?).
        '''
        return self._update_resolutions(
            self.document_file_info_dao.get_file_infos_for_document(document.id))

    def get_file_info_by_id(self, file_info_id):
        '''
        Returns the file info for a given file id
        '''
        
        return self._update_resolution(self.document_file_info_dao.get_by_id(file_info_id))

    def get_file_for_file_info(self, file_info):
        '''
        Returns the path to the file described by the file_info
        '''
        
        return self.document_file_manager.get_file_path(file_info)
            
    def get_pdf(self, document):
        '''
        Returns the document pdf file as byte string
        '''
        return self.document_file_provider.get_pdf(document)
    
    def get_thumbnail(self, document_file_info):
        '''
        Returns a thumbnail for the document as byte string
        '''
        return self.document_file_provider.get_thumbnail(document_file_info)
    
    def get_display_image(self, document_file_info):
        '''
        Returns a graphical representation of the document as byte string
        '''
        return self.document_file_provider.get_display_image(document_file_info)

    def create_new(self):
        '''
        Just calls the document constructor to get a new Document entity.
        '''
        # pylint: disable=no-self-use
        document = Document()
        document.document_type = self.document_type_dao.get_by_id(1)
        return document
    
    def _update_resolution(self, file_info):
        '''
        The resolution information in the database is not complete (due to
        historical reasons). This is an auxiliary method to correct this
        until the database is cleaned up.
        '''
        if not file_info.resolution is None:
            return file_info
        
        if file_info.filetype == 'gif':
            # More historical debt: gif files always have a resolution of 72 dpi,
            # but in the early days we scanned with 300 dpi and saved them as gif,
            # so the gif seems to be too large. So in fact we have to interpret
            # the resolution as 300
            file_info.resolution = get_gif_file_resolution(None)
            return file_info
        
        if file_info.filetype in ('jpg', 'png', 'tif'):
            try:
                file_path = self.document_file_manager.get_file_path(file_info)
            except DocumentFileNotFound:
                return self._set_default_resolution(file_info)

            file_info.resolution = get_graphic_file_resolution(file_path)
            if not file_info.resolution:
                file_info = self._set_default_resolution(file_info)
        
        return file_info
    
    # pylint: disable=no-self-use    
    def _set_default_resolution(self, file_info):    
        if file_info.filetype == 'jpg':
            file_info.resolution = 72
        else:
            file_info.resolution = 300
        return file_info
        
    def _update_resolutions(self, file_info_list):
        updated_list = []
        for file_info in file_info_list:
            updated_list.append(self._update_resolution(file_info))
        return updated_list
        