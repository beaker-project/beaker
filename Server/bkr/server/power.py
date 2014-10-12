
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import (expose, flash, widgets, error_handler,
                        redirect, paginate, url)
from kid import Element, XML
from bkr.server.widgets import AlphaNavBar, myPaginateDataGrid, HorizontalForm
from bkr.server.model import PowerType
from bkr.server.admin_page import AdminPage

def make_link(url, text):
    # make a <a> element
    a = Element('a', href='./' + url)
    a.text = text
    return a
 	
def make_edit_link(power):
    # make a edit link
    return make_link(url  = 'edit?id=%s' % power.id,
                     text = power.name)

def make_remove_link(power):
    # make a remove link
    return XML('<a class="btn" href="remove?id=%s">'
            '<i class="fa fa-times"/> Remove</a>' % power.id)

def get_power_type(power):
    # return powertype name
    return make_link(url  = '../powertypes/edit?id=%s' % power.powertype.id,
                     text = power.powertype.name)

class PowerTypes(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    id         = widgets.HiddenField(name='id')
    name       = widgets.TextField(name='name', label=_(u'Name'))

    form = HorizontalForm(
        'powertypes',
        fields = [id, name],
        action = 'save_data',
        submit_text = _(u'Save'),
    )


    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/powertypes/by_name?anywhere=1"),
        kw['search_name'] = 'power'
        super(PowerTypes,self).__init__(*args,**kw)

        self.search_col = PowerType.name
        self.search_mapper = PowerType
      

    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.form,
            title=_(u'New Power Type'),
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='bkr.server.templates.form')
    def edit(self,**kw):
        title = _(u'New Power Type')
        values = []
        if kw.get('id'):
            powertype = PowerType.by_id(kw['id'])
            title = powertype.name
            values = dict(
                id         = powertype.id,
                name       = powertype.name,
            )
        
        return dict(
            form = self.form,
            title=title,
            action = './save',
            options = {},
            value = values,
        )
    
    @expose()
    @error_handler(edit)
    def save(self, **kw):
        if kw['id']:
            edit = PowerType.by_id(kw['id'])
            edit.name = kw['name']
        elif kw.get('name'):
            new = PowerType(name=kw['name'])
            session.add(new)
        else:
            flash(_(u"Invalid Power Type entry"))
            redirect(".")
        flash( _(u"OK") )
        redirect(".")

    @expose(format='json')
    def by_name(self,input,*args,**kw): 
        if 'anywhere' in kw:
            search = PowerType.list_by_name(input,find_anywhere=True)
        else:
            search = PowerType.list_by_name(input)

        powers = [elem.name for elem in search]
        return dict(matches=powers)

    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list', default_order='name', limit=20)
    def index(self,*args,**kw):
        powertypes = session.query(PowerType)
        list_by_letters = set([elem.name[0].capitalize() for elem in powertypes if elem.name])
        results = self.process_search(**kw)
        if results:
            powertypes = results

        powertypes_grid = myPaginateDataGrid(fields=[
                                  ('Power Type', make_edit_link),
                                  (' ', make_remove_link),
                              ],
                              add_action='./new')
        

        return dict(title="Power Types", 
                    grid = powertypes_grid,
                    search_widget = self.search_widget_form,
                    alpha_nav_bar = AlphaNavBar(list_by_letters,'power'),
                    list = powertypes)

    @expose()
    def remove(self, **kw):
        remove = PowerType.by_id(kw['id'])
        session.delete(remove)
        flash( _(u"%s Deleted") % remove.name )
        raise redirect(".")

