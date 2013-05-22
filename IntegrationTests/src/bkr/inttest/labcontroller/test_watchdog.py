
import os, os.path
import time
from turbogears.database import session
from bkr.common.helpers import makedirs_ignore
from bkr.labcontroller.config import get_conf
from bkr.server.model import LogRecipe
from bkr.inttest import data_setup
from bkr.inttest.assertions import wait_for_condition
from bkr.inttest.labcontroller import LabControllerTestCase

class WatchdogConsoleLogTest(LabControllerTestCase):

    @classmethod
    def setUpClass(cls):
        makedirs_ignore(get_conf().get('CONSOLE_LOGS'), 0755)

    def setUp(self):
        with session.begin():
            self.system = data_setup.create_system(lab_controller=self.get_lc())
            self.recipe = data_setup.create_recipe()
            data_setup.create_job_for_recipes([self.recipe])
            data_setup.mark_recipe_running(self.recipe, system=self.system)
        self.console_log = os.path.join(get_conf().get('CONSOLE_LOGS'), self.system.fqdn)
        self.cached_console_log = os.path.join(get_conf().get('CACHEPATH'), 'recipes',
                str(self.recipe.id // 1000) + '+', str(self.recipe.id), 'console.log')

    def check_console_log_registered(self):
        with session.begin():
            return LogRecipe.query.filter_by(parent=self.recipe,
                    filename=u'console.log').count() == 1

    def test_stores_console_log(self):
        first_line = 'Here is the first line of the log file.\n'
        open(self.console_log, 'w').write(first_line)
        wait_for_condition(self.check_console_log_registered)
        self.assertEquals(open(self.cached_console_log, 'r').read(), first_line)

        second_line = 'Here is the second line of the log file. FNORD FNORD FNORD\n'
        open(self.console_log, 'a').write(second_line)
        def log_updated():
            return open(self.cached_console_log, 'r').read() == (first_line + second_line)
        wait_for_condition(log_updated)

    # https://bugzilla.redhat.com/show_bug.cgi?id=962901
    def test_console_log_not_recreated_after_removed(self):
        # The scenario for this bug is:
        # 1. beaker-watchdog writes the console log
        # 2. recipe finishes (but beaker-watchdog hasn't noticed yet)
        # 3. beaker-transfer tranfers the logs and removes the local copies
        # 4. beaker-watchdog writes more to the end of the console log (in the 
        # process re-registering the log file, and leaving the start of the 
        # file filled with zeroes)
        # 5. beaker-transfer tranfers the logs again
        # This test checks that step 4 is prevented -- the console log updates 
        # are silently discarded instead.

        # Step 1: beaker-watchdog writes the console log
        existing_data = 'Existing data\n'
        open(self.console_log, 'w').write(existing_data)
        wait_for_condition(self.check_console_log_registered)
        self.assertEquals(open(self.cached_console_log, 'r').read(), existing_data)

        # Step 2: the recipe "finishes"
        # Don't actually mark it as finished in the database though, to ensure 
        # the watchdog keeps monitoring the console log.

        # Step 3: beaker-transfer tranfers the logs and removes the local copies
        with session.begin():
            LogRecipe.query.filter_by(parent=self.recipe,
                    filename=u'console.log').one().server = u'http://elsewhere'
        os.remove(self.cached_console_log)

        # Step 4: beaker-watchdog tries to write more to the end of the console log
        open(self.console_log, 'a').write(
                'More console output, after the recipe has finished\n')
        # Give beaker-watchdog a chance to notice
        time.sleep(get_conf().get('SLEEP_TIME') * 2)

        self.assert_(not os.path.exists(self.cached_console_log))
        with session.begin():
            self.assertEquals(LogRecipe.query.filter_by(parent=self.recipe,
                    filename=u'console.log').one().server,
                    u'http://elsewhere')
