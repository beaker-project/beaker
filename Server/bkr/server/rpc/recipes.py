
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import logging
from datetime import datetime, timedelta

from lxml import etree
from sqlalchemy import not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.database import session
from bkr.common.bexceptions import BX
from bkr.server import identity, dynamic_virt
from bkr.server.rpc import expose, register
from bkr.server.rpc.recipetasks import RecipeTasks
from bkr.server.util import ensure_str
from bkr.server.model import (Recipe, RecipeSet, TaskStatus, Job, System,
                              SystemResource, VirtResource,
                              LogRecipe, LogRecipeTask, LogRecipeTaskResult,
                              RecipeReservationRequest,
                              RecipeReservationCondition)
from six.moves import urllib


logger = logging.getLogger(__name__)


@register('recipes')
class Recipes(object):
    # For XMLRPC methods in this class.
    exposed = True

    tasks = RecipeTasks()

    log_types = dict(R = LogRecipe,
                     T = LogRecipeTask,
                     E = LogRecipeTaskResult,
                    )

    @expose
    @identity.require(identity.not_anonymous())
    def by_log_server(self, server, limit=50):
        """
        Returns a list of recipe IDs which have logs stored on the given
        server. By default, returns at most 50 at a time.

        Only returns recipes where the whole recipe set has completed. Also
        excludes recently completed recipe sets, since the system may continue
        uploading logs for a short while until beaker-provision powers it off.
        """
        finish_threshold = datetime.utcnow() - timedelta(minutes=2)
        recipes = Recipe.query.join(Recipe.recipeset)\
                .join(RecipeSet.job)\
                .filter(not_(Job.is_deleted))\
                .filter(RecipeSet.status.in_([s for s in TaskStatus if s.finished]))\
                .filter(not_(RecipeSet.recipes.any(Recipe.finish_time >= finish_threshold)))\
                .filter(Recipe.log_server == server)\
                .limit(limit)
        return [recipe_id for recipe_id, in recipes.values(Recipe.id)]

    @expose
    @identity.require(identity.not_anonymous())
    def register_file(self, server, recipe_id, path, filename, basepath):
        """
        register file and return path to store
        """
        try:
            recipe = Recipe.by_id(recipe_id, lockmode='update')
        except NoResultFound:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        if recipe.is_finished():
            raise BX('Cannot register file for finished recipe %s'
                    % recipe.t_id)

        # Add the log to the DB if it hasn't been recorded yet.
        log_recipe = LogRecipe.lazy_create(recipe_id=recipe.id,
                                           path=path,
                                           filename=filename,
                                          )
        log_recipe.server = server
        log_recipe.basepath = basepath
        # Pull log_server out of server_url.
        recipe.log_server = urllib.parse.urlparse(server)[1]
        return '%s' % recipe.filepath

    @expose
    @identity.require(identity.not_anonymous())
    def files(self, recipe_id):
        """
        Return an array of logs for the given recipe.

        :param recipe_id: id of recipe
        :type recipe_id: integer

        .. deprecated:: 0.9.4
           Use :meth:`taskactions.files() <bkr.server.task_actions.taskactions.files>` instead.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        # Build a list of logs excluding duplicate paths, to mitigate:
        # https://bugzilla.redhat.com/show_bug.cgi?id=963492
        logdicts = []
        seen_paths = set()
        for log in recipe.all_logs():
            logdict = log.dict
            # The path we care about here is the path which beaker-transfer 
            # will move the file to.
            # Don't be tempted to use os.path.join() here since log['path'] 
            # is often '/' which does not give the result you would expect.
            path = os.path.normpath('%s/%s/%s' % (logdict['filepath'],
                    logdict['path'], logdict['filename']))
            if path in seen_paths:
                logger.warn('%s contains duplicate log %s', log.parent.t_id, path)
            else:
                seen_paths.add(path)
                logdicts.append(logdict)
        return logdicts

    @expose
    @identity.require(identity.in_group('lab_controller'))
    def change_files(self, recipe_id, server, basepath):
        """
        Change the server and basepath where the log files lives, Usually
         used to move from lab controller cache to archive storage.
        """
        try:
            recipe = Recipe.by_id(recipe_id, lockmode='update')
        except NoResultFound:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        for mylog in recipe.all_logs():
            mylog.server = '%s/%s/' % (server, mylog.parent.filepath)
            mylog.basepath = '%s/%s/' % (basepath, mylog.parent.filepath)
        recipe.log_server = urllib.parse.urlparse(server)[1]
        return True

    @expose
    @identity.require(identity.not_anonymous())
    def extend(self, recipe_id, kill_time):
        """
        Extend recipe watchdog by kill_time seconds
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        return recipe.extend(kill_time)

    @expose
    def console_output(self, recipe_id, output_length=None, offset=None):
        """
        Get text console log output from OpenStack
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        manager = dynamic_virt.VirtManager(recipe.recipeset.job.owner)
        return manager.get_console_output(recipe.resource.instance_id, output_length)

    @expose
    def watchdog(self, recipe_id):
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        return recipe.status_watchdog()

    @expose
    @identity.require(identity.not_anonymous())
    def stop(self, recipe_id, stop_type, msg=None):
        """
        Set recipe status to Completed
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX('Invalid recipe ID: %s' % recipe_id)
        if not recipe.recipeset.can_stop(identity.current.user):
            raise BX("You don't have permission to stop recipe %s"
                     % recipe_id)
        if stop_type not in recipe.stop_types:
            raise BX('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, recipe.stop_types))
        kwargs = dict(msg = msg)
        return getattr(recipe,stop_type)(**kwargs)

    @expose
    @identity.require(identity.not_anonymous())
    def install_start(self, recipe_id=None):
        """
        Records the start of a recipe's installation. The watchdog is extended
        by 3 hours to allow the installation to complete.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX("Invalid Recipe ID %s" % recipe_id)
        if not recipe.installation:
            raise BX('Recipe %s not provisioned yet' % recipe_id)

        installation = recipe.installation
        if not installation.install_started:
            installation.install_started = datetime.utcnow()
            # extend watchdog by 3 hours 60 * 60 * 3
            kill_time = 10800
            logger.debug('Extending watchdog for %s', recipe.t_id)
            recipe.extend(kill_time)
            return True
        else:
            logger.debug('Already recorded install_started for %s', recipe.t_id)
            return False

    @expose
    @identity.require(identity.not_anonymous())
    def install_fail(self, recipe_id=None):
        """
        Records the fail of a recipe's installation.
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX("Invalid Recipe ID {}".format(recipe_id))  # noqa: F821
        if not recipe.installation:
            raise BX("Recipe {} not provisioned yet".format(recipe_id))  # noqa: F821

        return recipe.abort('Installation failed')

    @expose
    @identity.require(identity.not_anonymous())
    def postinstall_done(self, recipe_id=None):
        """
        Report completion of postinstallation
        """
        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX(u'Invalid Recipe ID %s' % recipe_id)
        if not recipe.installation:
            raise BX('Recipe %s not provisioned yet' % recipe_id)
        recipe.installation.postinstall_finished = datetime.utcnow()
        return True

    @expose
    @identity.require(identity.not_anonymous())
    def install_done(self, recipe_id=None, fqdn=None):
        """
        Report completion of installation with current FQDN
        """
        if not recipe_id:
            raise BX("No recipe id provided!")

        try:
            recipe = Recipe.by_id(recipe_id)
        except InvalidRequestError:
            raise BX("Invalid Recipe ID %s" % recipe_id)
        if not recipe.installation:
            raise BX('Recipe %s not provisioned yet' % recipe_id)

        recipe.installation.install_finished = datetime.utcnow()
        # We don't want to change an existing FQDN, just set it
        # if it hasn't been set already (see BZ#879146)
        configured = recipe.resource.fqdn
        if configured is None and fqdn:
            recipe.resource.fqdn = configured = fqdn
        elif configured != fqdn:
            # We use eager formatting here to make this easier to test
            logger.info("Configured FQDN (%s) != reported FQDN (%s) in R:%s" %
                     (configured, fqdn, recipe_id))
        return configured

    @expose
    @identity.require(identity.not_anonymous())
    def postreboot(self, recipe_id=None):
        # Backwards compat only, delete this after 0.10:
        # the recipe_id arg used to be hostname
        try:
            int(recipe_id)
        except ValueError:
            system = System.by_fqdn(recipe_id, identity.current.user)
            system.action_power('reboot', service=u'XMLRPC', delay=30)
            return system.fqdn

        try:
            recipe = Recipe.by_id(int(recipe_id))
        except (InvalidRequestError, NoResultFound, ValueError):
            raise BX('Invalid recipe ID %s' % recipe_id)
        if isinstance(recipe.resource, SystemResource):
            recipe.resource.system.action_power('reboot',
                    service=u'XMLRPC', delay=30)
        return True

    @expose
    def to_xml(self, recipe_id=None):
        """
            Pass in recipe id and you'll get that recipe's xml
        """
        if not recipe_id:
            raise BX("No recipe id provided!")
        try:
            recipexml = etree.tostring(Recipe.by_id(recipe_id).to_xml(),
                                       pretty_print=True, encoding='utf8')
        except InvalidRequestError:
            raise BX("Invalid Recipe ID %s" % recipe_id)
        return ensure_str(recipexml)
