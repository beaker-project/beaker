import unittest
import tempfile
import logging
import os
from glob import glob
from bkr.labcontroller.utils import add_rotating_file_logger
from bkr.labcontroller.config import get_conf
from bkr.inttest.data_setup import unique_name

# This number (300) has been tested to work with
# 1024 and 2 as the maxbytes and backupcount
_log_print_count = 300
_log_maxbytes = 1024
_log_backupcount = 2

class TestLogs(unittest.TestCase):

    def setUp(self):
        self.conf = get_conf()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.propagate = False
        self.logger.setLevel(logging.DEBUG)
        prefix = unique_name(u'watchdogtest%s')
        self.log_file = tempfile.NamedTemporaryFile(prefix=prefix)
        add_rotating_file_logger(self.logger, self.log_file.name,
            maxBytes=_log_maxbytes, backupCount=_log_backupcount,
            log_level=logging.DEBUG)

    def teardown(self):
        files_to_delete = glob('%s*' % self.log_file.name)
        for filename in files_to_delete:
            os.remove(filename)
        self.logger.handlers[:] = []

    def test_log_size(self):
        test_string = 'testingsize'
        for i in range(_log_print_count):
            self.logger.debug(test_string)
        log_file_name = self.log_file.name
        current_log_size = os.path.getsize(self.log_file.name)
        # Check our current log file size.
        # In reality the log should be about a byte bigger than
        # our config value
        self.assert_(current_log_size <= _log_maxbytes + 8)
        rotated_logs_size = []
        for i in range(_log_backupcount):
            rotated_logs_size.append(os.path.getsize('%s.%d' % (self.log_file.name, i + 1)))
        # Test that we have the correct number of backups have been made
        self.assert_(len(rotated_logs_size) == _log_backupcount)
        for log_size in rotated_logs_size:
            self.assert_(log_size <= _log_maxbytes + 8)
