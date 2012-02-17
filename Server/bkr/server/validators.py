from turbogears import validators, identity
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.model import System, Recipe

class CheckRecipeValid(validators.TgFancyValidator):

    def _to_python(self, value, state):
        try:
            recipe = Recipe.by_id(value)
        except NoResultFound:
            raise validators.Invalid('Invalid recipe', value, state)
        return recipe


class CheckSystemValid(validators.TgFancyValidator):

    def _to_python(self, value, state):
        try:
            system = System.by_fqdn(value, identity.current.user)
        except NoResultFound:
            raise validators.Invalid('Invalid system', value, state)
        return system

class GroupFormSchema(validators.Schema):
    display_name = validators.UnicodeString(not_empty=True, max=256, strip=True)
    group_name = validators.UnicodeString(not_empty=True, max=256, strip=True)
