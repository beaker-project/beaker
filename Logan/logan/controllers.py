# Logan - Logan is the scheduling piece of the Beaker project
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import turbogears as tg
from turbogears import controllers, expose, flash
# from logan import model
from turbogears import identity, redirect
from cherrypy import request, response
# from logan import json
# import logging
# log = logging.getLogger("logan.controllers")
from logan.xmlrpccontroller import RPCRoot
from logan.jobs import Jobs
from logan.recipes import Recipes
from logan.tests import Tests
from logan.families import Families
from logan.arches import Arches
import fedora.tg.util
from turbogears import scheduler
import turbogears
import logan.jobs

turbogears.startup.call_on_startup.append(logan.jobs.schedule)

class Root(RPCRoot):
    jobs = Jobs()
    recipes = Recipes()
    tests = Tests()
    families = Families()
    arches = Arches()

    @expose(template="logan.templates.welcome")
    # @identity.require(identity.in_group("admin"))
    def index(self):
        import time
        # log.debug("Happy TurboGears Controller Responding For Duty")
        flash("Your application is now running")
        return dict(now=time.ctime())

    @expose(template="logan.templates.login")
    @expose(allow_json=True)
    def login(self, forward_url=None, previous_url=None, *args, **kw):

        if not identity.current.anonymous and identity.was_login_attempted() \
                and not identity.get_identity_errors():
            # User is logged in
            if 'json' == fedora.tg.util.request_format():
                return dict(user=identity.current.user)
            if not forward_url:
                forward_url = turbogears.url('/')
            raise redirect(tg.url(forward_url or previous_url or '/', kw))

        forward_url = None
        previous_url = request.path

        if identity.was_login_attempted():
            msg = _("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg = _("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg = _("Please log in.")
            forward_url = request.headers.get("Referer", "/")

        response.status = 403
        return dict(message=msg, previous_url=previous_url, logging_in=True,
            original_parameters=request.params, forward_url=forward_url)

    @expose(allow_json=True)
    def logout(self):
        identity.current.logout()
        if 'json' in fedora.tg.util.request_format():
            return dict()
        raise redirect("/")
