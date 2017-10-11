
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import (expose, flash, widgets, redirect)
from flask import request, jsonify
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.app import app
from bkr.server.flask_util import auth_required, convert_internal_errors, \
    BadRequest400, NotFound404, Forbidden403, read_json_request
from bkr.server.model import RecipeSet, TaskStatus, TaskPriority, TaskBase, \
    Job, RecipeSetComment, session
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import BeakerException

import cherrypy

import logging
log = logging.getLogger(__name__)

def _get_rs_by_id(id):
    try:
        return RecipeSet.by_id(id)
    except NoResultFound:
        raise NotFound404('Recipe set %s not found' % id)

@app.route('/recipesets/<int:id>', methods=['GET'])
def get_recipeset(id):
    """
    Provides detailed information about a recipe set in JSON format.

    :param id: ID of the recipe set.
    """
    recipeset = _get_rs_by_id(id)
    return jsonify(recipeset.__json__())

def _update_recipeset(recipeset, data=None):
    if not data:
        data = {}
    def record_activity(field, old=None, new=None, action=u'Changed'):
        recipeset.record_activity(user=identity.current.user, service=u'HTTP',
                action=action, field=field, old=old, new=new)
    with convert_internal_errors():
        if 'priority' in data:
            priority = TaskPriority.from_string(data['priority'])
            if priority != recipeset.priority:
                if not recipeset.can_change_priority(identity.current.user):
                    raise Forbidden403('Cannot change recipe set %s priority' % recipeset.id)
                allowed = recipeset.allowed_priorities(identity.current.user)
                if priority not in allowed:
                    raise Forbidden403('Cannot set recipe set %s priority to %s, '
                            'permitted priorities are: %s'
                            % (recipeset.id, priority, ' '.join(unicode(pri) for pri in allowed)))
                record_activity(u'Priority', old=recipeset.priority.value, new=priority.value)
                recipeset.priority = priority
        if 'waived' in data:
            if not isinstance(data['waived'], bool):
                raise ValueError('waived key must be true or false')
            waived = data['waived']
            if waived != recipeset.waived:
                if not recipeset.can_waive(identity.current.user):
                    raise Forbidden403('Cannot waive recipe set %s' % recipeset.id)
                record_activity(u'Waived', old=unicode(recipeset.waived), new=unicode(waived))
                recipeset.waived = waived

@app.route('/recipesets/<int:id>', methods=['PATCH'])
@auth_required
def update_recipeset(id):
    """
    Updates the attributes of a recipe set. The request must be 
    :mimetype:`application/json`.

    :param id: ID of the recipe set.
    :jsonparam string priority: Priority for the recipe set. Must be one of 
      'Low', 'Medium', 'Normal', 'High', or 'Urgent'. This can only be changed 
      while a recipe set is still queued. Job owners can generally only 
      *decrease* the priority of their recipe set, queue admins can increase 
      it.
    :jsonparam boolean waived: If true, the recipe set will be waived, regardless
      of its result.
    """
    recipeset = _get_rs_by_id(id)
    data = read_json_request(request)
    _update_recipeset(recipeset, data)
    return jsonify(recipeset.__json__())

@app.route('/recipesets/by-taskspec/<taskspec>', methods=['PATCH'])
@auth_required
def update_recipeset_by_taskspec(taskspec):
    """
    Updates the attributes of a recipe set identified by a taskspec. The valid type
    of a taskspec is either J(job) or RS(recipe-set). If a taskspec format is
    J:<id>, all the recipe sets in this job will be updated. The request must be
    :mimetype:`application/json`.

    :param taskspec: A taskspec argument that identifies a job or recipe set.
    :jsonparam string priority: Priority for the recipe set. Must be one of 
      'Low', 'Medium', 'Normal', 'High', or 'Urgent'. This can only be changed 
      while a recipe set is still queued. Job owners can generally only 
      *decrease* the priority of their recipe set, queue admins can increase 
      it.
    :jsonparam boolean waived: If true, the recipe set will be waived, regardless
      of its result.
    """
    if not taskspec.startswith(('J', 'RS')):
        raise BadRequest400('Taskspec type must be one of [J, RS]')
    try:
        obj = TaskBase.get_by_t_id(taskspec)
    except BeakerException as exc:
        raise NotFound404(unicode(exc))
    data = read_json_request(request)
    if isinstance(obj, Job):
        for rs in obj.recipesets:
            _update_recipeset(rs, data)
    elif isinstance(obj, RecipeSet):
        _update_recipeset(obj, data)
    return jsonify(obj.__json__())

@app.route('/recipesets/<int:id>/status', methods=['POST'])
@auth_required
def update_recipeset_status(id):
    """
    Updates the status of a recipe set. The request must be :mimetype:`application/json`.

    Currently the only allowed value for status is 'Cancelled', which has the 
    effect of cancelling all recipes in the recipe set that have not finished yet.

    :param id: ID of the recipe set.
    :jsonparam string status: The new status. Must be 'Cancelled'.
    :jsonparam string msg: A message describing the reason for updating the status.
    """
    recipeset = _get_rs_by_id(id)
    if not recipeset.can_cancel(identity.current.user):
        raise Forbidden403('Cannot update recipe set status')
    data = read_json_request(request)
    if 'status' not in data:
        raise BadRequest400('Missing status')
    status = TaskStatus.from_string(data['status'])
    msg = data.get('msg', None) or None
    if status != TaskStatus.cancelled:
        raise BadRequest400('Status must be "Cancelled"')
    with convert_internal_errors():
        recipeset.record_activity(user=identity.current.user, service=u'HTTP',
                field=u'Status', action=u'Cancelled')
        recipeset.cancel(msg=msg)
    return '', 204

@app.route('/recipesets/<int:id>/comments/', methods=['GET'])
def get_recipeset_comments(id):
    """
    Returns a JSON collection of comments made on a recipe set.

    :param id: ID of the recipe set.
    """
    recipeset = _get_rs_by_id(id)
    with convert_internal_errors():
        return jsonify({'entries': recipeset.comments})

@app.route('/recipesets/<int:id>/comments/', methods=['POST'])
@auth_required
def post_recipeset_comment(id):
    """
    Adds a new comment to a recipe set. The request must be :mimetype:`application/json`.

    :param id: ID of the recipe set.
    :jsonparam string comment: Comment text.
    """
    recipeset = _get_rs_by_id(id)
    if not recipeset.can_comment(identity.current.user):
        raise Forbidden403('Cannot post recipe set comment')
    data = read_json_request(request)
    if 'comment' not in data:
        raise BadRequest400('Missing "comment" key')
    with convert_internal_errors():
        comment = RecipeSetComment(user=identity.current.user,
                comment=data['comment'])
        recipeset.comments.append(comment)
    session.flush() # to populate the id
    return jsonify(comment.__json__())

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
