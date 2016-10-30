'''
Created on 29.01.2015

@author: archivar
'''
import unittest

from alexandriabase.domain import AlexDate, AlexDateRange, InvalidDateException, \
    alex_date_from_key


class ConfigTests(unittest.TestCase):

    def testDateValidationNonIntYear(self):
        
        exception = None
        try:
            AlexDate(year="bla")
        except InvalidDateException as e:
            exception = e
        self.assertEqual("bla is not a valid year!", str(exception))
            
    def testDateValidationYearOutOfRange(self):
        
        exception = None
        try:
            AlexDate(year=3001)
        except InvalidDateException as e:
            exception = e
        self.assertEqual("Year 3001 is out of range (0-3000)!", str(exception))
            
    def testDateValidationYear(self):
        
        exception = None
        try:
            AlexDate(year=1970)
        except InvalidDateException as e:
            exception = e
        self.assertFalse(exception)

    def testDateValidationNonIntMonth(self):
        
        exception = None
        try:
            AlexDate(year=1970, month="bla")
        except InvalidDateException as e:
            exception = e
        self.assertEqual("bla is not a valid month!", str(exception))
            
    def testDateValidationMonthOutOfRange(self):
        
        exception = None
        try:
            AlexDate(year=1970, month=13)
        except InvalidDateException as e:
            exception = e
        self.assertEqual("Month 13 is out of range (1-12)!", str(exception))
            
    def testDateValidationYearAndMonth(self):
        
        exception = None
        try:
            AlexDate(year=1970, month=12)
        except InvalidDateException as e:
            exception = e
        self.assertFalse(exception)

    def testDateValidationNonIntDay(self):
        
        exception = None
        try:
            AlexDate(year=1970, month=12, day="bla")
        except InvalidDateException as e:
            exception = e
        self.assertEqual("bla is not a valid day!", str(exception))
            
    def testDateValidationDayOutOfRange(self):
        
        exception = None
        try:
            AlexDate(year=1970, month=12, day=32)
        except InvalidDateException as e:
            exception = e
        self.assertEqual("Day 32 is out of range (1-31)!", str(exception))
            
    def testDateValidationYearAndMonthAndDay(self):
        
        exception = None
        try:
            AlexDate(year=1970, month=12, day=31)
        except InvalidDateException as e:
            exception = e
        self.assertFalse(exception)

    def testDateValidationCombinedFail(self):
        
        exception = None
        try:
            AlexDate(year=1971, month=2, day=29)
        except InvalidDateException as e:
            exception = e
        self.assertEqual("Illegal date: 29.2.1971!", str(exception))

    def testDateValidationCombinedWorking(self):
        
        exception = None
        try:
            AlexDate(year=1972, month=2, day=29)
        except InvalidDateException as e:
            exception = e
        self.assertFalse(exception)

    def testDateJustYear(self):
        date = alex_date_from_key(1940000007)
        self.assertEqual(date.year, 1940)
        self.assertEqual(date.month, None)
        self.assertEqual(date.day, None)

    def testDateYearAndMonth(self):
        date = alex_date_from_key(1940010007)
        self.assertEqual(date.year, 1940)
        self.assertEqual(date.month, 1)
        self.assertEqual(date.day, None)

    def testDateComplete(self):
        date = alex_date_from_key(1940053007)
        self.assertEqual(date.year, 1940)
        self.assertEqual(date.month, 5)
        self.assertEqual(date.day, 30)

    def testCreateKeyJustYear(self):
        input_key = 1940000007
        date = alex_date_from_key(input_key)
        output_key = date.as_key(7)
        self.assertEqual(input_key, output_key)

    def testCreateKeyYearAndMonth(self):
        input_key = 1940010007
        date = alex_date_from_key(input_key)
        output_key = date.as_key(7)
        self.assertEqual(input_key, output_key)

    def testCreateKeyComplete(self):
        input_key = 1940010507
        date = alex_date_from_key(input_key)
        output_key = date.as_key(7)
        self.assertEqual(input_key, output_key)

    def testToStringJustYear(self):
        daterange = AlexDateRange(1940000001, None)
        self.assertEqual(str(daterange), "1940")

    def testToStringYearAndMonth(self):
        daterange = AlexDateRange(1940040001, None)
        self.assertEqual(str(daterange), "April 1940")

    def testToStringYearAndMonthAndDay(self):
        daterange = AlexDateRange(1940041301, None)
        self.assertEqual(str(daterange), "13. April 1940")

    def testToStringBothYear(self):
        daterange = AlexDateRange(1940000000, 1941000000)
        self.assertEqual(str(daterange), "1940 - 1941")

    def testToStringBothYearAndMonth(self):
        daterange = AlexDateRange(1940040001, 1942080000)
        self.assertEqual(str(daterange), "April 1940 - August 1942")

    def testToStringBothYearAndMonthAndDar(self):
        daterange = AlexDateRange(1940041301, 1942081400)
        self.assertEqual(str(daterange), "13. April 1940 - 14. August 1942")
    
    # Full comparison: 3 Tests    
    def testComparisonAllValuesSetEqual(self):
        date1 = AlexDate(1940, 12, 31)
        date2 = AlexDate(1940, 12, 31)
        self.assertDateEqual(date1, date2)

    def testComparisonAllValuesSetGreater(self):
        date1 = AlexDate(1940, 12, 31)
        date2 = AlexDate(1940, 12, 30)
        self.assertDateGreater(date1, date2)

    def testComparisonAllValuesSetSmaller(self):
        date1 = AlexDate(1940, 12, 29)
        date2 = AlexDate(1940, 12, 30)
        self.assertDateSmaller(date1, date2)
        
    # One day missing: 4 Tests
    def testComparisonOneDayMissingGreater(self):
        date1 = AlexDate(1940, 12, None)
        date2 = AlexDate(1940, 11, 30)
        self.assertDateGreater(date1, date2)
    
    def testComparisonOneDayMissingSmaller(self):
        date1 = AlexDate(1940, 12, None)
        date2 = AlexDate(1940, 12, 30)
        self.assertDateSmaller(date1, date2)
        
    def testComparisonOtherOneDayMissingGreater(self):
        date1 = AlexDate(1940, 12, 1)
        date2 = AlexDate(1940, 12, None)
        self.assertDateGreater(date1, date2)
        
    def testComparisonOtherOneDayMissingSmaller(self):
        date1 = AlexDate(1940, 11, 30)
        date2 = AlexDate(1940, 12, None)
        self.assertDateSmaller(date1, date2)
        
    # Both one day missing: 3 Tests
    def testComparisonBothDayMissingSetEqual(self):
        date1 = AlexDate(1940, 12, None)
        date2 = AlexDate(1940, 12, None)
        self.assertDateEqual(date1, date2)
        
    def testComparisonBothDaysMissingSetGreater(self):
        date1 = AlexDate(1940, 12, None)
        date2 = AlexDate(1940, 11, None)
        self.assertDateGreater(date1, date2)
        
    def testComparisonBothDaysMissingSetSmaller(self):
        date1 = AlexDate(1940, 11, None)
        date2 = AlexDate(1940, 12, None)
        self.assertDateSmaller(date1, date2)

    # One month missing, other full: 4 Tests
    def testComparisonMonthMissingOtherFullGreater(self):
        date1 = AlexDate(1940, None, None)
        date2 = AlexDate(1939, 11, 30)
        self.assertDateGreater(date1, date2)
    
    def testComparisonMonthMissingOtherFullSmaller(self):
        date1 = AlexDate(1940, None, None)
        date2 = AlexDate(1940, 1, 1)
        self.assertDateSmaller(date1, date2)

    def testComparisonFullOtherMonthMissingGreater(self):
        date1 = AlexDate(1939, 1, 1)
        date2 = AlexDate(1939, None, None)
        self.assertDateGreater(date1, date2)
    
    def testComparisonFullOtherMonthMissingSmaller(self):
        date1 = AlexDate(1939, 12, 31)
        date2 = AlexDate(1940, None, None)
        self.assertDateSmaller(date1, date2)

    # One month missing, other day missing: 4 Tests
    def testComparisonMonthMissingOtherDayMissngGreater(self):
        date1 = AlexDate(1940, None, None)
        date2 = AlexDate(1939, 12, None)
        self.assertDateGreater(date1, date2)
    
    def testComparisonMonthMissingOtherDayMissingSmaller(self):
        date1 = AlexDate(1940, None, None)
        date2 = AlexDate(1940, 1, None)
        self.assertDateSmaller(date1, date2)

    def testComparisonDayMissingOtherMonthMissingGreater(self):
        date1 = AlexDate(1939, 1, None)
        date2 = AlexDate(1939, None, None)
        self.assertDateGreater(date1, date2)
    
    def testComparisonDayMissingOtherMonthMissingSmaller(self):
        date1 = AlexDate(1939, 12, None)
        date2 = AlexDate(1940, None, None)
        self.assertDateSmaller(date1, date2)
        
    # Both month missing: 3 Tests
    def testComparisonBothMonthsMissingSetEqual(self):
        date1 = AlexDate(1940, None, None)
        date2 = AlexDate(1940, None, None)
        self.assertDateEqual(date1, date2)
        
    def testComparisonBothMonthsMissingSetGreater(self):
        date1 = AlexDate(1941, None, None)
        date2 = AlexDate(1940, None, None)
        self.assertDateGreater(date1, date2)
        
    def testComparisonBothMonthsMissingSetSmaller(self):
        date1 = AlexDate(1939, None, None)
        date2 = AlexDate(1940, None, None)
        self.assertDateSmaller(date1, date2)

    def assertDateEqual(self, date1, date2):
        self.assertFalse(date1 > date2)
        self.assertFalse(date1 < date2)
        self.assertTrue(date1 == date2)
        self.assertTrue(date1 >= date2)
        self.assertTrue(date1 <= date2)

    def assertDateSmaller(self, date1, date2):
        self.assertFalse(date1 > date2)
        self.assertTrue(date1 < date2)
        self.assertFalse(date1 == date2)
        self.assertFalse(date1 >= date2)
        self.assertTrue(date1 <= date2)

    def assertDateGreater(self, date1, date2):
        self.assertTrue(date1 > date2)
        self.assertFalse(date1 < date2)
        self.assertFalse(date1 == date2)
        self.assertTrue(date1 >= date2)
        self.assertFalse(date1 <= date2)


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'ConfigTests.testName']
    unittest.main()