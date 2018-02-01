import unittest2 as unittest
from mock import Mock
from tempfile import NamedTemporaryFile

from bkr.labcontroller.proxy import ConsoleLogHelper
from bkr.labcontroller.log_storage import LogFile


class ConsoleLogHelperTest(unittest.TestCase):

    # https://bugzilla.redhat.com/show_bug.cgi?id=1413827
    def test_process_log_successfully_catches_installation_failure(self):
        block1 = "This is a fatal error and install\n\n\n\n"
        block2 = "ation will be aborted" + "z" * 30 + "\n"
        temp_file = NamedTemporaryFile()

        fake_watchdog = dict(recipe_id=1)
        fake_proxy = Mock()
        fake_proxy.report_panic(fake_watchdog, False)
        fake_proxy.log_storage.recipe.return_value = LogFile(temp_file.name, lambda x: x)

        console_log_helper = ConsoleLogHelper(fake_watchdog, fake_proxy, "ignored")
        console_log_helper.process_log(block1)
        console_log_helper.process_log(block2)

        fake_proxy.report_install_failure.assert_called_with(fake_watchdog,
            'This is a fatal error and installation will be aborted')
