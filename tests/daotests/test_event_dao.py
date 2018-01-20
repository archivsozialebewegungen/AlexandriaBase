'''
Created on 11.10.2015

@author: michael
'''
from datetime import date
import unittest

from alexandriabase.base_exceptions import NoSuchEntityException
from alexandriabase.daos.basiccreatorprovider import BasicCreatorProvider
from alexandriabase.daos.creatordao import CreatorDao
from alexandriabase.daos.documentdao import DocumentDao,\
    DocumentFilterExpressionBuilder
from alexandriabase.daos.documenttypedao import DocumentTypeDao
from alexandriabase.daos.eventdao import EventDao, \
    EventFilterExpressionBuilder
from alexandriabase.daos.eventtypedao import EventTypeDao
from alexandriabase.domain import EventFilter, Event, AlexDateRange, \
    AlexDate
from daotests.test_base import DatabaseBaseTest
from alexandriabase.daos.relationsdao import DocumentEventRelationsDao


class TestEreignisDao(DatabaseBaseTest):

    def setUp(self):
        super().setUp()
        erfasser_dao = CreatorDao(self.engine)
        document_type_dao = DocumentTypeDao(self.engine)
        self.references_dao = DocumentEventRelationsDao(self.engine,
                                                        DocumentFilterExpressionBuilder(),
                                                        EventFilterExpressionBuilder())
        ereignistyp_dao = EventTypeDao(self.engine)
        creator_provider = BasicCreatorProvider(erfasser_dao)
        self.dao = EventDao(self.engine,
                               erfasser_dao,
                               self.references_dao,
                               ereignistyp_dao,
                               creator_provider)
        self.dokument_dao = DocumentDao(self.engine,
                               None,
                               erfasser_dao,
                               creator_provider,
                               document_type_dao)

    def testCompleteMappingAndGetFirst(self):
        ereignis = self.dao.get_first()
        self.assertTrue(ereignis, "Kein Ereignis bekommen!")
        self.assertEqual(ereignis.id, 1940000001)
        self.assertEqual(ereignis.key, 1940000001)
        self.assertEqual(ereignis.description, "Erstes Ereignis")
        self.assertEqual(str(ereignis.daterange), "1940")
        self.assertEqual(ereignis.status_id, 2)
        self.assertEqual(ereignis.erfasser.name, "Max Mustermann")
        self.assertEqual(ereignis.creation_date, date(2014, 12, 31))
        self.assertEqual(ereignis.change_date, date(2015, 1, 13))
        self.assertEqual(ereignis.location_id, 0)
        
    def testGetLast(self):
        ereignis = self.dao.get_last()
        self.assertEqual(ereignis.id, 1961050101)
        self.assertEqual(ereignis.erfasser.name, 'Erna Musterfrau')
        self.assertEqual(ereignis.creation_date, date(2014, 10, 31))

    def testGetById(self):
        ereignis = self.dao.get_by_id(1950000001)
        self.assertEqual(ereignis.erfasser.name, 'Erna Musterfrau')
        self.assertEqual(ereignis.creation_date, date(2014, 10, 31))

    def testGetNext(self):
        ereignis = self.dao.get_first()
        self.assertEqual(ereignis.id, 1940000001)
        ereignis = self.dao.get_next(ereignis)
        self.assertEqual(ereignis.id, 1950000001)
        ereignis = self.dao.get_next(ereignis)
        self.assertEqual(ereignis.id, 1960013001)
        ereignis = self.dao.get_next(ereignis)
        self.assertEqual(ereignis.id, 1961050101)
        # wrap around
        ereignis = self.dao.get_next(ereignis)
        self.assertEqual(ereignis.id, 1940000001)

    def testGetPrevious(self):
        ereignis = self.dao.get_last()
        self.assertEqual(ereignis.id, 1961050101)
        ereignis = self.dao.get_previous(ereignis)
        self.assertEqual(ereignis.id, 1960013001)
        ereignis = self.dao.get_previous(ereignis)
        self.assertEqual(ereignis.id, 1950000001)
        ereignis = self.dao.get_previous(ereignis)
        self.assertEqual(ereignis.id, 1940000001)
        # wrap around
        ereignis = self.dao.get_previous(ereignis)
        self.assertEqual(ereignis.id, 1961050101)
        
    def testGetNearest(self):
        event_id = 194000000
        nearest = self.dao.get_nearest(event_id)
        self.assertEqual(1940000001, nearest.id)
        event_id = 1941000000
        nearest = self.dao.get_nearest(event_id)
        self.assertEqual(1950000001, nearest.id)
        event_id = 1980000000
        nearest = self.dao.get_nearest(event_id)
        self.assertEqual(1961050101, nearest.id)

    def test_filtering(self):
        event_filter = EventFilter()
        event_filter.searchterms = ['weit', 'ritt', 'Zwei']
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event.id, 1950000001)
        event = self.dao.get_next(event, filter_expression)
        self.assertEqual(event.id, 1960013001)
        event = self.dao.get_next(event, filter_expression)
        self.assertEqual(event.id, 1950000001)
        event = self.dao.get_previous(event, filter_expression)
        self.assertEqual(event.id, 1960013001)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event.id, 1960013001)
        
    def test_filtering_II(self):
        event_filter = EventFilter()
        event_filter.searchterms = ["doesn't find anything"]
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event, None)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event, None)

    def test_filtering_earliest_date(self):
        event_filter = EventFilter()
        event_filter.earliest_date = AlexDate(1960)
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event.id, 1960013001)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event.id, 1961050101)

    def test_filtering_latest_date(self):
        event_filter = EventFilter()
        event_filter.latest_date = AlexDate(1960, 1, 30)
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event.id, 1940000001)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event.id, 1960013001)

    def test_filtering_local_only(self):
        event_filter = EventFilter()
        event_filter.local_only = True
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event.id, 1950000001)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event.id, 1961050101)

    def test_filtering_unverified_only(self):
        event_filter = EventFilter()
        event_filter.unverified_only = True
        filter_expression_builder = EventFilterExpressionBuilder()
        filter_expression = filter_expression_builder.create_filter_expression(event_filter)
        event = self.dao.get_first(filter_expression)
        self.assertEqual(event.id, 1961050101)
        event = self.dao.get_last(filter_expression)
        self.assertEqual(event.id, 1961050101)

    def test_save_new(self):
        exception_raised = False
        try:
            self.dao.get_by_id(1951010101)
        except NoSuchEntityException:
            exception_raised = True
        self.assertTrue(exception_raised)
        event = Event()
        event.daterange = AlexDateRange(1951010100, 1951010500)
        event.description = "New description"
        event.status_id = 1
        self.assertFalse(event.id)
        self.dao.save(event)
        self.assertTrue(event.id)
        self.assertEqual(event.id, 1951010101)
        event = self.dao.get_by_id(1951010101)
        self.assertTrue(event)
        self.assertEqual(event.erfasser.name, "Admin")
        self.assertEqual(event.description, "New description")
        self.assertEqual(event.status_id, 1)
        
    def test_simple_update_event(self):
        event = self.dao.get_by_id(1940000001)
        self.assertEqual(event.description, "Erstes Ereignis")
        event.description = "New description"
        self.dao.save(event)
        event = self.dao.get_by_id(1940000001)
        self.assertEqual(event.description, "New description")

    def test_key_update_event(self):
        referenced_ids = self.references_dao.fetch_document_ids_for_event_id(1950000002)
        self.assertEqual(len(referenced_ids), 0)
        event = self.dao.get_by_id(1940000001)
        event.daterange = AlexDateRange(1950000000, None)
        self.dao.save(event)
        exception_raised = False
        try:
            event = self.dao.get_by_id(1940000001)
        except NoSuchEntityException:
            exception_raised = True
        self.assertTrue(exception_raised)
        event = self.dao.get_by_id(1950000002)
        self.assertEqual(event.description, "Erstes Ereignis")
        referenced_ids = self.references_dao.fetch_document_ids_for_event_id(1950000002)
        self.assertTrue(len(referenced_ids) > 0)
        
    def test_get_next_free_sequence_id(self):
        alex_date = AlexDate(1940)
        self.assertEqual(self.dao._get_next_free_sequence_id(alex_date), 2)
        alex_date = AlexDate(1941)
        self.assertEqual(self.dao._get_next_free_sequence_id(alex_date), 1)
        
    def test_get_events_for_date(self):
        alex_date = AlexDate(1940)
        event_list = self.dao.get_events_for_date(alex_date)
        self.assertEqual(len(event_list), 1)
        self.assertEqual(event_list[0].id, 1940000001)
        
    def test_delete(self):
        referenced_ids = self.references_dao.fetch_document_ids_for_event_id(1940000001)
        number_of_references = len(referenced_ids)
        self.assertTrue(number_of_references > 0)
        self.dao.delete(1940000001)
        referenced_ids = self.references_dao.fetch_document_ids_for_event_id(1940000001)
        number_of_references = len(referenced_ids)
        self.assertEqual(number_of_references, 0)
        
if __name__ == "__main__":
    # import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
