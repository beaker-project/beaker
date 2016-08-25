
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.validators import FormValidator, Invalid, TgFancyValidator, \
        UnicodeString
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.model import System, Recipe, User, LabController, RetentionTag
from bkr.server.bexceptions import DatabaseLookupError

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
        except DatabaseLookupError:
            raise Invalid('Invalid system', value, state)
        return system


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
