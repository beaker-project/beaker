
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import cracklib
from turbogears.validators import FormValidator, Invalid, TgFancyValidator, \
        UnicodeString
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.model import System, Recipe, User, LabController, RetentionTag


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

class LabControllerFormValidator(FormValidator):

    __unpackargs__ = ('*', 'field_names')
    messages = {
        'fqdn_not_unique': 'FQDN is not unique',
    }

    def validate_python(self, form_fields, state):
        lc_id = form_fields.get('id', None)
        fqdn = form_fields['fqdn']

        try:
            existing_lc_with_fqdn = LabController.by_name(fqdn)
        except NoResultFound:
            existing_lc_with_fqdn = None

        if not lc_id:
            labcontroller = None
            luser = None
        else:
            labcontroller = LabController.by_id(lc_id)
            luser = labcontroller.user

        errors = {}
        if not labcontroller and existing_lc_with_fqdn:
            # New LC using duplicate FQDN
            errors['fqdn'] = self.message('fqdn_not_unique', state)
        elif (labcontroller and existing_lc_with_fqdn and
                labcontroller != existing_lc_with_fqdn):
            # Existing LC changing FQDN to a duplicate one
            errors['fqdn'] = self.message('fqdn_not_unique', state)
        if errors:
            raise Invalid('Validation failed', form_fields,
                    state, error_dict=errors)

class CheckRecipeValid(TgFancyValidator):

    def _to_python(self, value, state):
        try:
            recipe = Recipe.by_id(value)
        except NoResultFound:
            raise Invalid('Invalid recipe', value, state)
        return recipe


class CheckSystemValid(TgFancyValidator):

    def _to_python(self, value, state):
        try:
            system = System.by_fqdn(value, identity.current.user)
        except NoResultFound:
            raise Invalid('Invalid system', value, state)
        return system


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


class UniqueRetentionTag(FormValidator):

    __unpackargs__ = ('*', 'field_names')
    messages = {
        'not_unique': 'Retention tag already exists',
    }

    def validate_python(self, form_fields, state):
        id = form_fields.get('id')
        tag = form_fields['tag']
        existing = RetentionTag.query.filter_by(tag=tag).first()
        if existing and (not id or existing.id != id):
            error = self.message('not_unique', state)
            raise Invalid(error, form_fields, state, error_dict={'tag': error})
