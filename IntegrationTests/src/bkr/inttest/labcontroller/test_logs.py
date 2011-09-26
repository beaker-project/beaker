import unittest
import tempfile
import logging
import os
from glob import glob
from bkr.labcontroller.utils import add_rotating_file_logger
from bkr.inttest.data_setup import unique_name

# This number (300) has been tested to work with
# 1024 and 2 as the maxbytes and backupcount
_log_print_count = 300

class TestLogs(unittest.TestCase):

    def setUp(self):
        from bkr.inttest.labcontroller import conf
        self.conf = conf
        self.logger = logging.getLogger("Watchdog")
        self.logger.setLevel(logging.DEBUG)
        prefix = unique_name(u'watchdogtest%s')
        self.log_file = tempfile.NamedTemporaryFile(prefix=prefix)
        add_rotating_file_logger(self.logger, self.log_file.name, log_level=logging.DEBUG)

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
        maxbytes = self.conf.get('LOG_MAXBYTES')
        backup_count = self.conf.get('LOG_BACKUPCOUNT')
        # Check our current log file size.
        # In reality the log should be about a byte bigger than
        # our config value
        self.assert_(current_log_size <= maxbytes + 8)
        rotated_logs_size = []
        for i in range(backup_count):
            rotated_logs_size.append(os.path.getsize('%s.%d' % (self.log_file.name, i + 1)))
        # Test that we have the correct number of backups have been made
        self.assert_(len(rotated_logs_size) == backup_count)
        for log_size in rotated_logs_size:
            self.assert_(log_size <= maxbytes + 8)
