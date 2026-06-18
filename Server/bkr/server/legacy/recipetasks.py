
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import expose
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.model import RecipeTask
from bkr.server.rpc.recipetasks import RecipeTasks as RecipeTasksRPC


class RecipeTasks(RPCRoot, RecipeTasksRPC):
    exposed = True

    @expose(format='json')
    def to_xml(self, id):
        taskxml = RecipeTask.by_id(id).to_xml().toprettyxml()
        return dict(xml=taskxml)
