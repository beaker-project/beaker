import cherrypy
import sys
from datetime import datetime
from turbogears import widgets, expose, identity, validators, \
	error_handler, validate, flash, redirect, url
from turbogears.database import session
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.model import ConfigItem, SSHPubKey, User
from bkr.server import validators as beaker_validators
from bkr.server.widgets import BeakerDataGrid, DeleteLinkWidgetForm, \
    DoAndConfirmForm
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import NoChangeException
from bkr.server.helpers import make_link

from bexceptions import *

__all__ = ['Preferences']

class Preferences(RPCRoot):

    exposed = True
    delete_link = DeleteLinkWidgetForm()
    beaker_password = widgets.PasswordField(name='password', label='Beaker Password')
    root_password = widgets.TextField(name='_root_password', label='Root Password')
    rootpw_expiry = widgets.TextField(name='rootpw_expiry',
                                      label='Root Password Expiry',
                                      attrs={'disabled': True})
    email = widgets.TextField(name='email_address', label='Email Address',
                                   validator=beaker_validators.CheckUniqueEmail())
    prefs_form   = widgets.TableForm(
        'UserPrefs',
        fields = [email, beaker_password, root_password, rootpw_expiry],
        action = 'save',
        submit_text = _(u'Change'),
    )

    sshkey = widgets.TextArea(name='ssh_pub_key', label='Public SSH Key',
            validator=beaker_validators.SSHPubKey(not_empty=True))
    ssh_key_add_form = widgets.TableForm(
        'ssh_key_add',
        fields = [sshkey],
        action = 'ssh_key_add',
        submit_text = _(u'Add'),
    )

    rootpw_grid = BeakerDataGrid(fields=[
                    ('Root Password', lambda x: x.value),
                    ('Effective from', lambda x: x.valid_from)
                 ])

    auto_users = widgets.AutoCompleteField(name='user',
                                   search_controller = url("../users/by_name"),
                                   search_param = "input",
                                   result_name = "matches")
    submission_delegate_form = widgets.TableForm(
        'SubmissionDelegates',
        fields = [auto_users],
        action = 'save_data',
        submit_text = _(u'Add'),
    )
    remove_submission_delegate_link = DoAndConfirmForm()

    def show_submission_delegates(self, user):
        user_fields = [
            ('Submission Delegate', lambda x: x.display_name),
            ('Action', lambda x: self.remove_submission_delegate_link. \
                display({'delegate_id': x.user_id},
                action=url('remove_submission_delegate'), look='link',
                msg='Are you sure you want to remove %s as a submitter' % x,
                action_text='Remove (-)')),]
        return widgets.DataGrid(fields=user_fields)

    @expose(template='bkr.server.templates.prefs')
    @identity.require(identity.not_anonymous())
    def index(self, *args, **kw):
        user = identity.current.user

        # Show all future root passwords, and the previous five
        rootpw = ConfigItem.by_name('root_password')
        rootpw_values = rootpw.values().filter(rootpw.value_class.valid_from > datetime.utcnow())\
                       .order_by(rootpw.value_class.valid_from.desc()).all()\
                      + rootpw.values().filter(rootpw.value_class.valid_from <= datetime.utcnow())\
                       .order_by(rootpw.value_class.valid_from.desc())[:5]

        return dict(
            title        = 'User Prefs',
            delete_link  = self.delete_link,
            prefs_form   = self.prefs_form,
            ssh_key_form = self.ssh_key_add_form,
            widgets      = {},
            ssh_keys     = user.sshpubkeys,
            value        = user,
            rootpw       = rootpw.current_value(),
            rootpw_grid  = self.rootpw_grid,
            rootpw_values = rootpw_values,
            options      = None, 
            #Hack, to insert static content for submission_delegate
            remove_submission_delegate = self.remove_submission_delegate_link,
            submission_delegates_grid = self.show_submission_delegates(user),
            submission_delegate_form = self.submission_delegate_form)

    # XMLRPC interface
    @expose()
    @identity.require(identity.not_anonymous())
    def remove_submission_delegate_by_name(self, delegate_name, service=u'XMLRPC'):
        user = identity.current.user
        try:
           submission_delegate = User.by_user_name(delegate_name)
        except NoResultFound:
            raise BX(_(u'%s is not a valid user name' % delegate_name))
        try:
            user.remove_submission_delegate(submission_delegate, service=service)
        except ValueError:
            raise BX(_(u'%s is not a submission delegate of %s' % \
                (delegate_name, user)))
        return delegate_name

    # UI interface
    @expose()
    @identity.require(identity.not_anonymous())
    def remove_submission_delegate(self, delegate_id, service=u'WEBUI'):
        user = identity.current.user
        try:
           submission_delegate = User.by_id(delegate_id)
        except NoResultFound:
            flash(_(u'%s is not a valid user id' % delegate_id))
            redirect('.')
        user.remove_submission_delegate(submission_delegate, service=service)
        flash(_(u'%s removed as a submission delegate' % submission_delegate))
        redirect('.')

    # XMLRPC Interface
    @expose()
    @identity.require(identity.not_anonymous())
    def add_submission_delegate_by_name(self, new_delegate_name,
        service=u'XMLRPC'):
        user = identity.current.user
        new_delegate = User.by_user_name(new_delegate_name)
        if not new_delegate:
            raise BX(_(u'%s is not a valid user' % new_delegate_name))
        user.add_submission_delegate(new_delegate, service)
        return new_delegate_name

    # UI Interface
    @expose()
    @identity.require(identity.not_anonymous())
    def add_submission_delegate(self, **kwargs):
        user = identity.current.user
        new_delegate_name = kwargs['user']['text']
        new_delegate = User.by_user_name(new_delegate_name)
        if not new_delegate:
            msg = u'%s is not a valid user' % new_delegate_name
            log.warn(msg)
            flash(_(msg))
            redirect('.')

        try:
            user.add_submission_delegate(new_delegate, u'WEBUI')
        except NoChangeException, e:
            flash(_(unicode(e)))
            redirect('.')

        flash(_(u'Added %s as a submission delegate' % new_delegate_name))
        redirect('.')

    @expose()
    @identity.require(identity.not_anonymous())
    @error_handler(index)
    @validate(form=prefs_form)
    def save(self, *args, **kw):
        email = kw.get('email_address', None)
        beaker_password = kw.get('password', None)
        root_password = kw.get('_root_password', None)
        changes = []

        def _do_password_change(password):
            identity.current.user.password = password
            changes.append(u'Beaker password changed')

        if kw['password'] != identity.current.user.password:
            check_change_password = getattr(identity.current_provider,
                'can_change_password', None)
            if check_change_password:
                if check_change_password(identity.current.user.user_name):
                    _do_password_change(kw['password'])
                else:
                    changes.append(u'Cannot change password')
            else:
                _do_password_change(kw['password'])

        if email and email != identity.current.user.email_address:
            changes.append("Email address changed")
            identity.current.user.email_address = email

        if identity.current.user.root_password and not root_password:
            identity.current.user.root_password = None
            changes.append("Test host root password cleared")
        elif root_password and root_password != \
            identity.current.user.root_password:
            try:
                identity.current.user.root_password = root_password
                changes.append("Test host root password hash changed")
            except ValueError, msg:
                changes.append("Root password not changed: %s" % msg)

        if changes:
            flash(_(u', '.join(changes)))
        redirect('.')

    #XMLRPC method for updating user preferences
    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    @validate(validators=dict(email_address=beaker_validators.CheckUniqueEmail()))
    def update(self, email_address=None, tg_errors=None):
        """
        Update user preferences

        :param email_address: email address
        :type email_address: string
        """
        if tg_errors:
            raise BeakerException(', '.join(str(item) for item in tg_errors.values()))
        if email_address:
            if email_address == identity.current.user.email_address:
                raise BeakerException("Email address not changed: new address is same as before")
            else:
                identity.current.user.email_address = email_address

    @expose()
    @identity.require(identity.not_anonymous())
    def ssh_key_remove(self, *args, **kw):
        user = identity.current.user
        keyid = kw.get('id', None)

        try:
            key = SSHPubKey.by_id(keyid)
        except InvalidRequestError:
            flash(_(u"SSH key not found"))
            redirect('.')

        if user != key.user:
            flash(_(u"May not remove another user's keys"))
            redirect('.')

        session.delete(key)
        flash(_(u"SSH public key removed"))
        redirect('.')

    @expose()
    @identity.require(identity.not_anonymous())
    @error_handler(index)
    @validate(form=ssh_key_add_form)
    def ssh_key_add(self, ssh_pub_key=None):
        user = identity.current.user
        k = SSHPubKey(*ssh_pub_key)
        user.sshpubkeys.append(k)
        flash(_(u"SSH public key added"))
        redirect('.')

# for sphinx
prefs = Preferences
