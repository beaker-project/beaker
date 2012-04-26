from turbogears import identity
from turbogears.validators import FormValidator, Invalid, TgFancyValidator
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.model import System, Recipe, User


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


class UniqueEmail(FormValidator):

    __unpackargs__ = ('*', 'field_names')
    messages = {'not_unique' : 'Email address is not unique' }

    def __init__(self, *args, **kw):
        super(UniqueEmail, self).__init__(*args, **kw)
        if len(self.field_names) < 2:
            raise TypeError("UniqueEmail() requires at least two field names")

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
                try:
                    user_by_email = User.by_email_address(email_address)
                    user_by_id = User.by_id(user_id)
                    if user_by_id != user_by_email: # An existing email that is not theirs
                        raise ValueError
                except NoResultFound: # Changed email to new unique email
                    pass
        except ValueError:
            error = {'email_address' : self.message('not_unique', state)}
            raise Invalid('Email address is not unique', form_fields,
                state, error_dict=error)


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
