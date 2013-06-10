import cracklib
from turbogears.validators import FormValidator, Invalid, TgFancyValidator, Email
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.model import System, Recipe, User, LabController


class StrongPassword(TgFancyValidator):

    def _to_python(self, value, state):
        try:
            cracklib.VeryFascistCheck(value)
            return value
        except ValueError, msg:
            raise Invalid('Invalid password: %s' % str(msg), value, state)


class UniqueUserName(FormValidator):

    __unpackargs__ = ('*', 'field_names')
    messages = {'not_unique' : 'Login name is not unique' }

    def __init__(self, *args, **kw):
        super(UniqueUserName, self).__init__(*args, **kw)
        if len(self.field_names) < 2:
            raise TypeError("UniqueUserName() requires at least two field names")

    def validate_python(self, form_fields, state):
        user_id = form_fields['user_id']
        user_name = form_fields['user_name']
        existing_user = User.by_user_name(user_name)
        try:
            if not user_id: # New user
                if existing_user: # with a duplicate name
                    raise ValueError
            else:
                if existing_user:
                    current_user = User.by_id(user_id)
                    if current_user != existing_user:
                        raise ValueError
        except ValueError:
            error = {'user_name' : self.message('not_unique', state)}
            raise Invalid('Login name is not unique', form_fields,
                state, error_dict=error)


class UniqueFormEmail(FormValidator):

    """
    This FormValidator is designed to be used with the user form that
    is used by administrators to add new and modify existing users.
    This is not to be used in forms where users modify their
    own email.
    """

    __unpackargs__ = ('*', 'field_names')
    messages = {'not_unique' : 'Email address is not unique' }

    def validate_python(self, form_fields, state):
        user_id = form_fields.get('user_id')
        email_address = form_fields['email_address']
        try:
            if not user_id: # New user
                try:
                    User.by_email_address(email_address)
                except NoResultFound:
                    pass
                else:
                    raise ValueError
            else:
                _check_user_email(email_address, user_id)
        except ValueError:
            error = {'email_address' : self.message('not_unique', state)}
            raise Invalid('Email address is not unique', form_fields,
                state, error_dict=error)

class UniqueLabControllerEmail(FormValidator):


    __unpackargs__ = ('*', 'field_names')
    messages = {'not_unique' : 'Email address is not unique' }

    def validate_python(self, form_fields, state):
        lc_id = form_fields.get('id', None)
        email_address = form_fields['email']
        user_name = form_fields['lusername']

        try:
            User.by_email_address(email_address)
        except NoResultFound:
            email_is_used = False
        else:
            email_is_used = True

        if User.by_user_name(user_name):
            new_user = False
        else:
            new_user = True

        if not lc_id:
            labcontroller = None
            luser = None
        else:
            labcontroller = LabController.by_id(lc_id)
            luser = labcontroller.user

        try:
            if not labcontroller and email_is_used: # New LC using dupe email
                raise ValueError
            if new_user and email_is_used: #New user using dupe email
                raise ValueError
            if luser:
                _check_user_email(email_address, luser.user_id)
        except ValueError:
            error = {'email' : self.message('not_unique', state)}
            raise Invalid('Email address is not unique', form_fields,
                state, error_dict=error)


class CheckUniqueEmail(Email):

    """
    This is used to validate the email address of the currently logged in user
    Do not use as an admin validitating other users emails
    """

    def _to_python(self, value, state):
        super(CheckUniqueEmail, self)._to_python(value,state)
        user_id = identity.current.user.user_id
        try:
            _check_user_email(value, user_id)
        except ValueError:
            raise Invalid('Email address is not unique', value, state)
        return value

class CheckRecipeValid(TgFancyValidator):

    def _to_python(self, value, state):
        try:
            recipe = Recipe.by_id(value)
        except NoResultFound:
            raise validators.Invalid('Invalid recipe', value, state)
        return recipe


class CheckSystemValid(TgFancyValidator):

    def _to_python(self, value, state):
        try:
            system = System.by_fqdn(value, identity.current.user)
        except NoResultFound:
            raise validators.Invalid('Invalid system', value, state)
        return system


def _check_user_email(email_address, user_id):
    try:
        user_by_email = User.by_email_address(email_address)
    except NoResultFound: # Email not being used
        pass
    else:
        #raise ValueError
        user_by_id = User.by_id(user_id)
        if user_by_id != user_by_email: # An existing email that is not theirs
            raise ValueError

class SSHPubKey(TgFancyValidator):

    strip = True
    messages = {
        'invalid': 'The supplied value is not a valid SSH public key',
        'newline': 'SSH public keys may not contain newlines',
    }

    def _to_python(self, value, state):
        if not value:
            return None
        if '\n' in value:
            raise Invalid(self.message('newline', state), value, state)
        elements = value.split(None, 2)
        if len(elements) != 3:
            raise Invalid(self.message('invalid', state), value, state)
        return elements

    def _from_python(self, value, state):
        if isinstance(value, tuple):
            return ' '.join(value)
        return value
