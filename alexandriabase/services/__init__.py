'''
Package containing all the service modules.
'''
from injector import Module, ClassProvider, singleton, provider, inject

from alexandriabase import baseinjectorkeys
from alexandriabase.daos import DaoModule
from alexandriabase.services.creatorservice import CreatorService
from alexandriabase.services.document_pdf_generation_service import DocumentPdfGenerationService, \
    GraphicsPdfHandler, TextPdfHandler
from alexandriabase.services.documentfilemanager import DocumentFileManager,\
    DocumentFileImageGenerator, GraphicsImageGenerator, TextImageGenerator, PdfImageGenerator, \
    PdfImageExtractor, FileProvider, MovieImageGenerator
from alexandriabase.services.documentservice import DocumentService
from alexandriabase.services.documenttypeservice import DocumentTypeService
from alexandriabase.services.eventservice import EventService
from alexandriabase.services.fileformatservice import FileFormatService
from alexandriabase.services.referenceservice import ReferenceService
from alexandriabase.services.database_upgrade_service import DatabaseUpgradeService


class ServiceModule(Module):
    '''
    Injector module for the services.
    '''
    
    def configure(self, binder):
        dao_module = DaoModule()
        dao_module.configure(binder)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_MANAGER_KEY,
                    ClassProvider(DocumentFileManager), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_PDF_GENERATOR_KEY,
                    ClassProvider(DocumentPdfGenerationService), scope=singleton)
        binder.bind(baseinjectorkeys.GRAPHICS_PDF_HANDLER_KEY,
                    ClassProvider(GraphicsPdfHandler), scope=singleton)
        binder.bind(baseinjectorkeys.TEXT_PDF_HANDLER_KEY,
                    ClassProvider(TextPdfHandler), scope=singleton)
        binder.bind(baseinjectorkeys.EVENT_SERVICE_KEY,
                    ClassProvider(EventService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_SERVICE_KEY,
                    ClassProvider(DocumentService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_TYPE_SERVICE_KEY,
                    ClassProvider(DocumentTypeService), scope=singleton)
        binder.bind(baseinjectorkeys.REFERENCE_SERVICE_KEY,
                    ClassProvider(ReferenceService), scope=singleton)
        binder.bind(baseinjectorkeys.FILE_FORMAT_SERVICE,
                    ClassProvider(FileFormatService), scope=singleton)
        binder.bind(baseinjectorkeys.CREATOR_SERVICE_KEY,
                    ClassProvider(CreatorService), scope=singleton)
        binder.bind(baseinjectorkeys.DATABASE_UPGRADE_SERVICE_KEY,
                    ClassProvider(DatabaseUpgradeService), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_IMAGE_GENERATOR_KEY,
                    ClassProvider(DocumentFileImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.GRAPHICS_IMAGE_GENERATOR_KEY,
                    ClassProvider(GraphicsImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.TEXT_IMAGE_GENERATOR_KEY,
                    ClassProvider(TextImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.PDF_IMAGE_GENERATOR_KEY,
                    ClassProvider(PdfImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.MOVIE_IMAGE_GENERATOR_KEY,
                    ClassProvider(MovieImageGenerator), scope=singleton)
        binder.bind(baseinjectorkeys.PDF_IMAGE_EXTRACTOR_KEY,
                    ClassProvider(PdfImageExtractor), scope=singleton)
        binder.bind(baseinjectorkeys.DOCUMENT_FILE_PROVIDER,
                    ClassProvider(FileProvider), scope=singleton)

    @provider
    @inject
    def provide_pdf_handlers(self, 
                             graphics_handler: baseinjectorkeys.GRAPHICS_PDF_HANDLER_KEY,
                             text_handler: baseinjectorkeys.TEXT_PDF_HANDLER_KEY) -> baseinjectorkeys.PDF_HANDLERS_KEY:
        '''
        Returns the handlers to create pdf representations for certain
        file types.
        '''
        # pylint: disable=no-self-use
        
        return {'jpg': graphics_handler,
                'tif': graphics_handler,
                'gif': graphics_handler,
                'txt': text_handler}

    @provider
    @inject
    def provide_image_generators(self,
                                 graphics_image_generator: baseinjectorkeys.GRAPHICS_IMAGE_GENERATOR_KEY,
                                 text_image_generator: baseinjectorkeys.TEXT_IMAGE_GENERATOR_KEY,
                                 pdf_image_generator: baseinjectorkeys.PDF_IMAGE_GENERATOR_KEY,
                                 movie_image_generator: baseinjectorkeys.MOVIE_IMAGE_GENERATOR_KEY) -> baseinjectorkeys.IMAGE_GENERATORS_KEY:
        
        return {'jpg': graphics_image_generator,
                'tif': graphics_image_generator,
                'gif': graphics_image_generator,
                'txt': text_image_generator,
                'pdf': pdf_image_generator,
                'mpg': movie_image_generator}