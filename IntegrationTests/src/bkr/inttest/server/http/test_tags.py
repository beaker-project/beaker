# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import requests

from bkr.inttest import DatabaseTestCase, get_server_base
from bkr.server.model import DistroTag, session
from bkr.server.tests.data_setup import unique_name


class DistroTagsHTTPTest(DatabaseTestCase):

    def setUp(self):
        self.tag_name = unique_name(u'tag%s')
        with session.begin():
            session.add(DistroTag(tag=self.tag_name))
        self.s = requests.Session()

    def test_lists_tags(self):
        response = self.s.get(get_server_base() + 'tags',
                              headers={'Accept': 'application/json'})
        response.raise_for_status()
        tags = [entry['tag'] for entry in response.json()['entries']]
        self.assertIn(self.tag_name, tags)

    def test_filters_tags_by_query(self):
        response = self.s.get(get_server_base() + 'tags',
                              params={'q': 'tag:%s' % self.tag_name},
                              headers={'Accept': 'application/json'})
        response.raise_for_status()
        tags = [entry['tag'] for entry in response.json()['entries']]
        self.assertEqual([self.tag_name], tags)

    def test_entries_report_the_tag_id(self):
        with session.begin():
            expected_id = DistroTag.by_tag(self.tag_name).id
        response = self.s.get(get_server_base() + 'tags',
                              params={'q': 'tag:%s' % self.tag_name},
                              headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertEqual(expected_id, response.json()['entries'][0]['id'])

    def test_without_accept_header_the_collection_is_paged(self):
        with session.begin():
            for _ in range(25):
                session.add(DistroTag(tag=unique_name(u'paged%s')))
        unpaged = self.s.get(get_server_base() + 'tags',
                             headers={'Accept': 'application/json'})
        paged = self.s.get(get_server_base() + 'tags')
        unpaged.raise_for_status()
        paged.raise_for_status()
        self.assertIsNone(unpaged.json().get('page_size'))
        self.assertEqual(20, paged.json()['page_size'])
