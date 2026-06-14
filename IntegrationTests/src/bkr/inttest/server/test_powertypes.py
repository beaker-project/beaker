
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest
import requests
from bkr.inttest import get_server_base


class PowerTypesHTTPTest(unittest.TestCase):

    def test_get_power_types_as_json(self):
        response = requests.get(get_server_base() + 'powertypes/',
                                headers={'Accept': 'application/json'})
        response.raise_for_status()
        self.assertIn('power_types', response.json())
