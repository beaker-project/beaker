
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
from decimal import Decimal

import datetime
from sqlalchemy.sql import and_, or_
from sqlalchemy.sql.expression import true, false

from bkr.server.model import User, System, LabInfo, Device
from bkr.server.search_utility import lucene_to_sqlalchemy


class LuceneQueryTest(unittest.TestCase):

    def assert_clause_equals(self, actual, expected):
        # We should be able to use expected.compare(actual) but it seems most
        # complex SQLAlchemy ClauseElement types (e.g. FromGrouping) do not
        # actually implement comparison properly.
        # The poor man's version is to just compile it to SQL and do string
        # comparison.
        actual_compiled = actual.compile()
        expected_compiled = expected.compile()
        if (str(actual_compiled) != str(expected_compiled)
                or actual_compiled.params != expected_compiled.params):
            self.fail('SQLAlchemy clauses do not match\nActual: %s %s\nExpected: %s %s'
                    % (actual_compiled, actual_compiled.params,
                       expected_compiled, expected_compiled.params))

    def test_single_term(self):
        clause = lucene_to_sqlalchemy(u'user_name:rmancy',
                {'user_name': User.user_name},
                [User.user_name])
        self.assert_clause_equals(clause, User.user_name == u'rmancy')

    def test_multiple_terms(self):
        clause = lucene_to_sqlalchemy(
                u'user_name:rmancy email_address:rmancy@redhat.com',
                {'user_name': User.user_name, 'email_address': User.email_address},
                [User.user_name, User.email_address])
        self.assert_clause_equals(clause,
                and_(User.user_name == u'rmancy',
                     User.email_address == u'rmancy@redhat.com'))

    def test_quoted_term(self):
        clause = lucene_to_sqlalchemy(u'display_name:"Raymond Mancy"',
                {'display_name': User.display_name},
                [User.display_name])
        self.assert_clause_equals(clause, User.display_name == u'Raymond Mancy')

    def test_wildcards(self):
        clause = lucene_to_sqlalchemy(
                u'email_address:*rmancy*',
                {'user_name': User.user_name, 'email_address': User.email_address},
                [User.user_name, User.email_address])
        self.assert_clause_equals(clause, User.email_address.like('%rmancy%'))

    def test_default_field(self):
        clause = lucene_to_sqlalchemy(u'rmancy*',
                {'user_name': User.user_name, 'email_address': User.email_address},
                [User.user_name, User.email_address])
        self.assert_clause_equals(clause,
                or_(User.user_name.like(u'rmancy%'),
                    User.email_address.like(u'rmancy%')))

    def test_negation(self):
        clause = lucene_to_sqlalchemy(u'-user_name:rmancy',
                {'user_name': User.user_name},
                [User.user_name])
        self.assert_clause_equals(clause, User.user_name != u'rmancy')

    def test_integer_column(self):
        clause = lucene_to_sqlalchemy(u'memory:1024',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause, System.memory == 1024)
        # searching invalid numbers against a numeric column is just False
        clause = lucene_to_sqlalchemy(u'memory:much',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause, and_(false()))

    def test_numeric_column(self):
        clause = lucene_to_sqlalchemy(u'weight:1.2',
                {'weight': LabInfo.weight},
                [LabInfo.weight])
        self.assert_clause_equals(clause, LabInfo.weight == Decimal('1.2'))
        # searching invalid numbers against a numeric column is just False
        clause = lucene_to_sqlalchemy(u'weight:heavy',
                {'weight': LabInfo.weight},
                [LabInfo.weight])
        self.assert_clause_equals(clause, and_(false()))

    def test_datetime_column(self):
        clause = lucene_to_sqlalchemy(u'date_added:2014-09-08',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(System.date_added >= datetime.datetime(2014, 9, 8, 0, 0),
                     System.date_added <= datetime.datetime(2014, 9, 8, 23, 59, 59)))
        # searching invalid dates against a datetime column is just False
        clause = lucene_to_sqlalchemy(u'date_added:fnord',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause, and_(false()))

    def test_integer_range(self):
        clause = lucene_to_sqlalchemy(u'memory:[1024 TO 2048]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause,
                and_(System.memory >= 1024, System.memory <= 2048))
        clause = lucene_to_sqlalchemy(u'memory:[1024 TO *]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause,
                and_(System.memory >= 1024, true()))
        clause = lucene_to_sqlalchemy(u'memory:[* TO 2048]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause,
                and_(true(), System.memory <= 2048))
        clause = lucene_to_sqlalchemy(u'memory:[* TO *]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause, and_(true(), true()))
        clause = lucene_to_sqlalchemy(u'memory:[fnord TO blorch]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause, and_(false(), false()))

    def test_integer_exclusive_range(self):
        clause = lucene_to_sqlalchemy(u'memory:{1024 TO 2048]',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause,
                and_(System.memory > 1024, System.memory <= 2048))
        clause = lucene_to_sqlalchemy(u'memory:[1024 TO 2048}',
                {'memory': System.memory}, [System.memory])
        self.assert_clause_equals(clause,
                and_(System.memory >= 1024, System.memory < 2048))

    def test_datetime_range(self):
        clause = lucene_to_sqlalchemy(u'date_added:[2014-08-01 TO 2014-08-31]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(System.date_added >= datetime.datetime(2014, 8, 1, 0, 0),
                     System.date_added <= datetime.datetime(2014, 8, 31, 23, 59, 59)))
        clause = lucene_to_sqlalchemy(u'date_added:[2014-08-01 TO *]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(System.date_added >= datetime.datetime(2014, 8, 1, 0, 0),
                     true()))
        clause = lucene_to_sqlalchemy(u'date_added:[* TO 2014-08-31]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(true(),
                     System.date_added <= datetime.datetime(2014, 8, 31, 23, 59, 59)))
        clause = lucene_to_sqlalchemy(u'date_added:[* TO *]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause, and_(true(), true()))
        clause = lucene_to_sqlalchemy(u'date_added:[fnord TO blorch]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause, and_(false(), false()))

    def test_datetime_exclusive_range(self):
        clause = lucene_to_sqlalchemy(u'date_added:{2014-08-01 TO 2014-08-31]',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(System.date_added > datetime.datetime(2014, 8, 1, 0, 0),
                     System.date_added <= datetime.datetime(2014, 8, 31, 23, 59, 59)))
        clause = lucene_to_sqlalchemy(u'date_added:[2014-08-01 TO 2014-08-31}',
                {'date_added': System.date_added}, [System.date_added])
        self.assert_clause_equals(clause,
                and_(System.date_added >= datetime.datetime(2014, 8, 1, 0, 0),
                     System.date_added < datetime.datetime(2014, 8, 31, 23, 59, 59)))

    def test_string_range(self):
        clause = lucene_to_sqlalchemy(u'fqdn:[aaa TO zzz]',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause,
                and_(System.fqdn >= u'aaa', System.fqdn <= u'zzz'))
        clause = lucene_to_sqlalchemy(u'fqdn:[aaa TO *]',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause, and_(System.fqdn >= u'aaa', true()))
        clause = lucene_to_sqlalchemy(u'fqdn:[* TO zzz]',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause, and_(true(), System.fqdn <= u'zzz'))
        clause = lucene_to_sqlalchemy(u'fqdn:[* TO *]',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause, and_(true(), true()))

    def test_string_exclusive_range(self):
        clause = lucene_to_sqlalchemy(u'fqdn:{aaa TO zzz]',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause,
                and_(System.fqdn > u'aaa', System.fqdn <= u'zzz'))
        clause = lucene_to_sqlalchemy(u'fqdn:[aaa TO zzz}',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause,
                and_(System.fqdn >= u'aaa', System.fqdn < u'zzz'))

    def test_nonexistent_field(self):
        clause = lucene_to_sqlalchemy(u'favourite_color:green',
                {'user_name': User.user_name, 'email_address': User.email_address},
                [User.user_name, User.email_address])
        self.assert_clause_equals(clause, and_(false()))

    def test_unterminated_range(self):
        clause = lucene_to_sqlalchemy(u'[what?',
                {'user_name': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name == u'[what?')
        clause = lucene_to_sqlalchemy(u'user_name:[what?',
                {'user_name': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name == u'[what?')

    def test_malformed_range(self):
        # missing the "TO" separator
        clause = lucene_to_sqlalchemy(u'[what]',
                {'fqdn': System.fqdn, 'memory': System.memory},
                [System.fqdn, System.memory])
        self.assert_clause_equals(clause,
                or_(System.fqdn == u'[what]', false()))
        clause = lucene_to_sqlalchemy(u'memory:[1024, 2048]',
                {'fqdn': System.fqdn, 'memory': System.memory},
                [System.fqdn, System.memory])
        self.assert_clause_equals(clause, and_(false()))

    def test_unterminated_quote(self):
        clause = lucene_to_sqlalchemy(u'"what?',
                {'user_name': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name == u'"what?')
        clause = lucene_to_sqlalchemy(u'user_name:"what?',
                {'user_name': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name == u'"what?')

    def test_empty_term(self):
        clause = lucene_to_sqlalchemy(u'fqdn:""',
                {'fqdn': System.fqdn}, [System.fqdn])
        self.assert_clause_equals(clause, System.fqdn == u'')

    def test_any_value(self):
        clause = lucene_to_sqlalchemy(u'user:*',
                {'user': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name != None)
        clause = lucene_to_sqlalchemy(u'-user:*',
                {'user': User.user_name}, [User.user_name])
        self.assert_clause_equals(clause, User.user_name == None)

    def test_collection_relationship(self):
        clause = lucene_to_sqlalchemy(u'device.driver:e1000',
                {'fqdn': System.fqdn,
                 'device.driver': (System.devices, Device.driver)},
                [System.fqdn])
        self.assert_clause_equals(clause,
                System.devices.any(Device.driver == u'e1000'))
