from datetime import datetime
from turbogears import widgets, expose, identity, validators, \
	error_handler, validate, flash, redirect
from turbogears.database import session
from bkr.server.model import ConfigItem, SSHPubKey
from bkr.server import validators as beaker_validators
from bkr.server.widgets import BeakerDataGrid, DeleteLinkWidgetForm
from bkr.server.xmlrpccontroller import RPCRoot

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
            options      = None)

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
