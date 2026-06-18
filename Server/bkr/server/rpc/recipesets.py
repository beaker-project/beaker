
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.exc import InvalidRequestError
from bkr.common.bexceptions import BX
from bkr.server import identity
from bkr.server.model import RecipeSet
from bkr.server.rpc import expose, register


@register('recipesets')
class RecipeSets(object):
    # For XMLRPC methods in this class.
    exposed = True

    @expose
    @identity.require(identity.not_anonymous())
    def stop(self, recipeset_id, stop_type, msg=None):
        """
        Set recipeset status to Completed
        """
        try:
            recipeset = RecipeSet.by_id(recipeset_id)
        except InvalidRequestError:
            raise BX('Invalid recipeset ID: %s' % recipeset_id)
        if not recipeset.can_stop(identity.current.user):
            raise BX("You don't have permission to stop recipeset %s"
                     % recipeset_id)
        if stop_type not in recipeset.stop_types:
            raise BX('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, recipeset.stop_types))
        kwargs = dict(msg = msg)
        return getattr(recipeset,stop_type)(**kwargs)
