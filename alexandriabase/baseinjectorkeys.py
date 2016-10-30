'''
All the keys of the alexandria base module for
dependency injection
'''
from injector import Key


# pylint: disable=invalid-name
CONFIG_FILE_KEY = Key('config_file')
CONFIG_KEY = Key('config')

DBEngineKey = Key('db_engine')
SQLAlchemyConnectionKey = Key('connection')

DOCUMENT_FILE_MANAGER_KEY = Key('document_file_manager')

DocumentFilterExpressionBuilderKey = Key('document_filter_expression_builder')
EVENT_FILTER_EXPRESSION_BUILDER_KEY = Key('event_filter_expression_builder')

CreatorProvider = Key('creator_provider')

CREATOR_DAO_KEY = Key('erfasser_dao')
REGISTRY_DAO_KEY = Key('registry_dao')
DocumentTypeDaoKey = Key('document_type_dao')
EreignisDaoKey = Key('ereignis_dao')
DokumentDaoKey = Key('document_dao')
DOCUMENT_FILE_INFO_DAO_KEY = Key('document_file_info_dao')
RelationsDaoKey = Key('relations_dao')
EventTypeDaoKey = Key('ereignistyp_dao')
EventCrossreferencesDaoKey = Key('eventcrossreferences_dao')

EventServiceKey = Key('event_service')
DocumentServiceKey = Key('document_service')
DOCUMENT_TYPE_SERVICE_KEY = Key('document_type_service')
ReferenceServiceKey = Key('relations_service')
FILE_FORMAT_SERVICE = Key('file_format_service')
CREATOR_SERVICE_KEY = Key('creator_service')
DATABASE_UPGRADE_SERVICE_KEY = Key('database_upgrade_service')
DOCUMENT_FILE_PROVIDER = Key('document_file_provider')

DOCUMENT_PDF_GENERATOR_KEY = Key('document_pdf_generator')
PDF_HANDLERS_KEY = Key('pdf_handlers')
GRAPHICS_PDF_HANDLER_KEY = Key('graphics_pdf_handler')
TEXT_PDF_HANDLER_KEY = Key('text_pdf_handler')
PDF_IMAGE_EXTRACTOR_KEY = Key('pdf_image_extractor')

DOCUMENT_FILE_IMAGE_GENERATOR_KEY = Key('document_file_image_generator')
IMAGE_GENERATORS_KEY = Key('image_generators')
GRAPHICS_IMAGE_GENERATOR_KEY = Key('graphics_image_generator')
TEXT_IMAGE_GENERATOR_KEY = Key('text_image_generator')
PDF_IMAGE_GENERATOR_KEY = Key('pdf_image_generator')
MOVIE_IMAGE_GENERATOR_KEY = Key('movie_image_generator')
