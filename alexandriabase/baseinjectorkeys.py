'''
All the keys of the alexandria base module for
dependency injection
'''
from injector import BoundKey

# Need providers that return a list of objects
DOCUMENT_FILTER_EXPRESSION_BUILDER_KEY = BoundKey('document_filter_expression_builder')
EVENT_FILTER_EXPRESSION_BUILDER_KEY = BoundKey('event_filter_expression_builder')
PDF_HANDLERS_KEY = BoundKey('pdf_handlers')
IMAGE_GENERATORS_KEY = BoundKey('image_generators')

# Needs to be replaced in higher packages
CREATOR_PROVIDER_KEY = BoundKey('creator_provider')
