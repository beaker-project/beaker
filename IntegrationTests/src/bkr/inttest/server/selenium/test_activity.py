
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from bkr.inttest.server.selenium import WebDriverTestCase
from bkr.inttest.server.webdriver_utils import login, \
    check_activity_search_results, delete_and_confirm
from bkr.inttest import data_setup, get_server_base, with_transaction
from bkr.server.model import User, DistroActivity, SystemActivity, \
    GroupActivity, DistroTreeActivity

class ActivityTestWD(WebDriverTestCase):

    def setUp(self):
        self.browser = self.get_browser()

    def test_can_search_custom_service(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            act1 = distro_tree.record_activity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE', field=u'Nonesente',
                old=u'sdfas', new=u'sdfa', action=u'Removed')
            act2 = distro_tree.record_activity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE2', field=u'Noneseonce',
                old=u'bsdf', new=u'sdfas', action=u'Removed')
        b = self.browser
        b.get(get_server_base() + 'activity/distrotree')
        b.find_element_by_class_name('search-query').send_keys('service:TESTSERVICE')
        b.find_element_by_class_name('grid-filter').submit()
        check_activity_search_results(b, present=[act1], absent=[act2])

    def test_can_search_by_distro_tree_specifics(self):
        with session.begin():
            tree1 = data_setup.create_distro_tree(arch=u'i386')
            act1 = tree1.record_activity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE', field=u'Nonesente',
                old=u'sdfas', new=u'sdfa', action=u'Added')
            tree2 = data_setup.create_distro_tree(arch=u'x86_64')
            act2 = tree2.record_activity(
                user=User.by_user_name(data_setup.ADMIN_USER),
                service=u'TESTSERVICE2', field=u'Noneseonce',
                old=u'bsdf', new=u'sdfas', action=u'Added')
        b = self.browser
        b.get(get_server_base() + 'activity/distrotree')
        b.find_element_by_class_name('search-query').send_keys('distro_tree.arch:i386')
        b.find_element_by_class_name('grid-filter').submit()
        check_activity_search_results(b, present=[act1], absent=[act2])

    def test_can_search_by_system_name(self):
        with session.begin():
            sys1 = data_setup.create_system()
            act1 = sys1.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'omgwtfbbq')
            sys2 = data_setup.create_system()
            act2 = sys2.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'lollercopter')
        b = self.browser
        b.get(get_server_base() + 'activity/system')
        b.find_element_by_class_name('search-query').send_keys(
                'system.fqdn:%s' % sys1.fqdn)
        b.find_element_by_class_name('grid-filter').submit()
        check_activity_search_results(b, present=[act1], absent=[act2])

    def test_can_search_by_distro_name(self):
        with session.begin():
            distro1 = data_setup.create_distro()
            act1 = distro1.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'omgwtfbbq')
            distro2 = data_setup.create_distro()
            act2 = distro2.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'lollercopter')
        b = self.browser
        b.get(get_server_base() + 'activity/distro')
        b.find_element_by_class_name('search-query').send_keys(
                'distro.name:%s' % distro1.name)
        b.find_element_by_class_name('grid-filter').submit()
        check_activity_search_results(b, present=[act1], absent=[act2])

    def test_can_search_by_group_name(self):
        with session.begin():
            group1 = data_setup.create_group()
            act1 = group1.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'omgwtfbbq')
            group2 = data_setup.create_group()
            act2 = group2.record_activity(service=u'testdata',
                    user=User.by_user_name(data_setup.ADMIN_USER),
                    action=u'Nothing', field=u'Nonsense',
                    old=u'asdf', new=u'lollercopter')
        b = self.browser
        b.get(get_server_base() + 'activity/group')
        b.find_element_by_class_name('search-query').send_keys(
                'group.group_name:%s' % group1.group_name)
        b.find_element_by_class_name('grid-filter').submit()
        check_activity_search_results(b, present=[act1], absent=[act2])
