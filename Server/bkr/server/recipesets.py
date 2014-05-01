
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import (expose, flash, widgets, redirect)
from sqlalchemy.exc import InvalidRequestError
from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot

import cherrypy

from bkr.server.model import RecipeSet

import logging
log = logging.getLogger(__name__)

class RecipeSets(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to cancel?")
    message = widgets.TextArea(name='msg', label=_(u'Reason?'), help_text=_(u'Optional'))
    cancel_form = widgets.TableForm(
        'cancel_recipeset',
        fields = [hidden_id, message, confirm],
        action = 'really_cancel',
        submit_text = _(u'Yes')
    )
    @identity.require(identity.not_anonymous())
    @expose(template="bkr.server.templates.form")
    def cancel(self, id):
        """
        Confirm cancel recipeset
        """
        try:
            recipeset = RecipeSet.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid recipeset id %s" % id))
            redirect("/jobs/%s" % recipeset.job.id)
        if not recipeset.can_cancel(identity.current.user):
            flash(_(u"You don't have permission to cancel recipeset id %s" % id))
            redirect("/jobs/%s" % recipeset.job.id)
        return dict(
            title = 'Cancel RecipeSet %s' % id,
            form = self.cancel_form,
            action = './really_cancel',
            options = {},
            value = dict(id = recipeset.id,
                         confirm = 'really cancel recipeset %s?' % id),
        )
    @identity.require(identity.not_anonymous())
    @expose()
    def really_cancel(self, id, msg=None):
        """
        Confirm cancel recipeset
        """
        try:
            recipeset = RecipeSet.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid recipeset id %s" % id))
            redirect("/jobs/%s" % recipeset.job.id)
        if not recipeset.can_cancel(identity.current.user):
            flash(_(u"You don't have permission to cancel recipeset id %s" % id))
            redirect("/jobs/%s" % recipeset.job.id)
        recipeset.cancel(msg)
        recipeset.record_activity(user=identity.current.user, service=u'WEBUI',
                                  field=u'Status', action=u'Cancelled', old='',
                                  new='')
        flash(_(u"Successfully cancelled recipeset %s" % id))
        redirect("/jobs/%s" % recipeset.job.id)

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, recipeset_id, stop_type, msg=None):
        """
        Set recipeset status to Completed
        """
        try:
            recipeset = RecipeSet.by_id(recipeset_id)
        except InvalidRequestError:
            raise BX(_('Invalid recipeset ID: %s' % recipeset_id))
        if stop_type not in recipeset.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, recipeset.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(recipeset,stop_type)(**kwargs)
