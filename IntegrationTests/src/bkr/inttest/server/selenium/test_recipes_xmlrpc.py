
from turbogears.database import session
from bkr.inttest import data_setup
from bkr.inttest.server.selenium import XmlRpcTestCase

class RecipesXmlRpcTest(XmlRpcTestCase):

    def setUp(self):
        with session.begin():
            self.lc = data_setup.create_labcontroller()
            self.lc.user.password = u'logmein'
        self.server = self.get_server()

    # https://bugzilla.redhat.com/show_bug.cgi?id=817518
    def test_by_log_server_only_returns_completed_recipesets(self):
        with session.begin():
            dt = data_setup.create_distro_tree()
            completed_recipe = data_setup.create_recipe(distro_tree=dt)
            incomplete_recipe = data_setup.create_recipe(distro_tree=dt)
            job = data_setup.create_job_for_recipes(
                    [completed_recipe, incomplete_recipe])
            job.recipesets[0].lab_controller = self.lc
            data_setup.mark_recipe_complete(completed_recipe,
                    system=data_setup.create_system(lab_controller=self.lc))
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        result = self.server.recipes.by_log_server(self.lc.fqdn)
        self.assertEqual(result, [])

    def test_install_done_updates_resource_fqdn(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            guestrecipe = data_setup.create_guestrecipe(host=recipe,
                    distro_tree=distro_tree)
            data_setup.create_job_for_recipes([recipe, guestrecipe])
            data_setup.mark_recipe_running(recipe)
            data_setup.mark_recipe_waiting(guestrecipe)
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        fqdn = 'theguestname'
        result = self.server.recipes.install_done(guestrecipe.id, fqdn)
        self.assertEqual(result, fqdn)
        with session.begin():
            session.expire(guestrecipe.resource)
            self.assertEqual(guestrecipe.resource.fqdn, fqdn)

    # https://bugzilla.redhat.com/show_bug.cgi?id=879146
    def test_install_done_preserves_system_resource_fqdn(self):
        with session.begin():
            distro_tree = data_setup.create_distro_tree()
            recipe = data_setup.create_recipe(distro_tree=distro_tree)
            system = data_setup.create_system(lab_controller=self.lc)
            initial_fqdn = system.fqdn
            data_setup.create_job_for_recipes([recipe])
            data_setup.mark_recipe_waiting(recipe, system=system)
            self.assertEqual(recipe.resource.fqdn, initial_fqdn)
        self.server.auth.login_password(self.lc.user.user_name, u'logmein')
        result = self.server.recipes.install_done(recipe.id, 'somename')
        self.assertEqual(result, initial_fqdn)
        with session.begin():
            session.expire(recipe.resource)
            self.assertEqual(recipe.resource.fqdn, initial_fqdn)
