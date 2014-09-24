
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose, validate
from cherrypy import HTTPError
from bkr.server import mail, identity
from bkr.server.model import System, Recipe, SystemActivity
from bkr.server.validators import CheckSystemValid, CheckRecipeValid

class SystemAction(object):

    @expose(format='json')
    @identity.require(identity.not_anonymous())
    @validate(validators = {'system' : CheckSystemValid(),
        'recipe_id' : CheckRecipeValid(),})
    def report_system_problem(self, system, description, recipe_id=None, tg_errors=None, **kw):
        if tg_errors:
            raise HTTPError(status=400, message=tg_errors)
        # CheckRecipeValid has converted the id into an ORM object
        if recipe_id is not None:
            recipe = recipe_id
        else:
            recipe = None
        mail.system_problem_report(system, description,
            recipe, identity.current.user)
        system.record_activity(user=identity.current.user, service=u'WEBUI',
                action=u'Reported problem', field=u'Status',
                old=None, new=description)
        return {}
