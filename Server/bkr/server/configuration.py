
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, widgets, error_handler, validators, redirect, paginate, url
from bkr.server import identity
from bkr.server.helpers import make_link, make_edit_link
from bkr.server.widgets import BeakerDataGrid, myPaginateDataGrid, AlphaNavBar, \
        HorizontalForm
from bkr.server.admin_page import AdminPage
from datetime import datetime

from bkr.server.model import ConfigItem

class Configuration(AdminPage):
    exposed = False

    id         = widgets.HiddenField(name='id')
    value_str  = widgets.TextArea(name='value', label=_(u'Value'))
    value_int  = widgets.TextField(name='value', label=_(u'Value'), validator=validators.Int())
    valid_from = widgets.TextField(name='valid_from',
                                   label=_(u'Effective from date'),
                                   help_text=u"Enter date and time (YYYY-MM-DD HH:MM) in the future or leave blank for setting to take immediate effect")

    string_form = HorizontalForm(
        'configitem',
        fields = [id, value_str, valid_from],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    int_form = HorizontalForm(
        'configitem',
        fields = [id, value_int, valid_from],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    value_grid = BeakerDataGrid(fields=[
                    ('Value', lambda x: x.value),
                    ('Effective from', lambda x: x.valid_from, {'datetime': True}),
                    ('Set by', lambda x: x.user),
                    ('Date set', lambda x: x.modified, {'datetime': True}),
                    ('', lambda x: x.valid_from <= datetime.utcnow() and " " or \
                                   make_link(url = 'delete?item=%s&id=%s' % (x.config_item.id, x.id), text = 'Delete')),
                 ])

    def __init__(self,*args,**kw):
        kw['search_url'] = url("/configuration/by_name?anywhere=1"),
        kw['search_name'] = 'name'
        super(Configuration, self).__init__(*args, **kw)

        self.search_col = ConfigItem.name
        self.search_mapper = ConfigItem

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.config_edit')
    def edit(self,**kw):
        if kw.get('id'):
            item = ConfigItem.by_id(kw['id'])
            form_values = dict(
                id         = item.id,
                numeric    = item.numeric,
                value      = item.current_value()
            )
        else:
            flash(_(u"Error: No item ID specified"))
            raise redirect(".")

        # Show all future values, and the previous five
        config_values = item.values().filter(item.value_class.valid_from > datetime.utcnow()).order_by(item.value_class.valid_from.desc()).all() \
                      + item.values().filter(item.value_class.valid_from <= datetime.utcnow()).order_by(item.value_class.valid_from.desc())[:5]

        if item.readonly:
            form = None
        elif item.numeric:
            form = self.int_form
        else:
            form = self.string_form

        return dict(
            title = item.name,
            subtitle = item.description,
            form = form,
            action = './save',
            options = {},
            value = form_values,
            list = config_values,
            grid = self.value_grid,
            warn_msg = item.readonly and "This item is read-only",
        )

    @expose()
    @error_handler(edit)
    @identity.require(identity.in_group("admin"))
    def save(self, **kw):
        if 'id' in kw and kw['id']:
            item = ConfigItem.by_id(kw['id'])
        else:
            flash(_(u"Error: No item ID"))
            raise redirect(".")
        if kw['valid_from']:
            try:
                valid_from = datetime.strptime(kw['valid_from'], '%Y-%m-%d %H:%M')
            except ValueError:
                flash(_(u"Invalid date and time specification, use: YYYY-MM-DD HH:MM"))
                raise redirect("/configuration/edit?id=%d" % item.id)
        else:
            valid_from = None

        try:
            item.set(kw['value'], valid_from, identity.current.user)
        except Exception, msg:
            flash(_(u"Failed to save setting: %s" % msg))
            raise redirect("/configuration/edit?id=%d" % item.id)

        flash(_(u"%s saved" % item.name))
        redirect(".")

    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list')
    def index(self, *args, **kw):
        configitems = session.query(ConfigItem)
        list_by_letters = set([elem.name[0].capitalize() for elem in configitems])
        results = self.process_search(**kw)
        if results:
            configitems = results
        configitems_grid = myPaginateDataGrid(fields=[
                                  ('Setting', lambda x: make_edit_link(x.name, x.id)),
                                  ('Description', lambda x: x.description),
                                  ('Current Value', lambda x: x.current_value()),
                                  ('Next Value', lambda x: x.next_value() and u'"%s" from %s' % (x.next_value().value, x.next_value().valid_from)),
                                  (' ', lambda x: (x.readonly or x.current_value() is None) and " " or
                                        make_link(url='remove?id=%s' % x.id,
                                            elem_class='btn', text='Clear current value')),
                              ])
        return dict(title="Configuration",
                    grid = configitems_grid,
                    alpha_nav_bar = AlphaNavBar(list_by_letters, self.search_name),
                    search_widget = self.search_widget_form,
                    list = configitems)

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, **kw):
        item = ConfigItem.by_id(kw['id'])
        item.set(None, None, identity.current.user)
        session.add(item)
        session.flush()
        flash(_(u"%s cleared") % item.description)
        raise redirect(".")

    @identity.require(identity.in_group("admin"))
    @expose()
    def delete(self, **kw):
        item = ConfigItem.by_id(kw['item'])
        val = item.value_class.by_id(kw['id'])
        if val.valid_from <= datetime.utcnow():
            flash(_(u"Cannot remove past value of %s") % item.name)
            raise redirect("/configuration/edit?id=%d" % item.id)
        session.delete(val)
        session.flush()
        flash(_(u"Future value of %s cleared") % item.name)
        raise redirect(".")

    @identity.require(identity.in_group("admin"))
    @expose(format='json')
    def by_name(self, input, *args, **kw):
        if 'anywhere' in kw:
            search = ConfigItem.list_by_name(input, find_anywhere=True)
        else:
            search = ConfigItem.list_by_name(input)

        keys = [elem.name for elem in search]
        return dict(matches=keys)
