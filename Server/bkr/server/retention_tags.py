
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from kid import XML
from turbogears.database import session
from turbogears import expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from bkr.server import identity
from bkr.server.widgets import myPaginateDataGrid, HorizontalForm
from bkr.server.admin_page import AdminPage
from bkr.server.model import RetentionTag as Tag
from bkr.server.helpers import make_edit_link
from bkr.server.validators import UniqueRetentionTag

import logging
log = logging.getLogger(__name__)

class TagFormSchema(validators.Schema):
    id = validators.Int()
    tag = validators.UnicodeString(not_empty=True, max=20, strip=True)
    default = validators.StringBool(if_empty=False)
    expire_in_days = validators.Int()
    needs_product = validators.StringBool(if_empty=False)
    chained_validators = [UniqueRetentionTag('id', 'tag')]

class RetentionTag(AdminPage):
    exposed = False

    tag = widgets.TextField(name='tag', label=_(u'Tag'))
    default = widgets.SingleSelectField(name='default', label=(u'Default'),
            options=[(0,'False'),(1,'True')])
    id = widgets.HiddenField(name='id') 
    expire_in_days = widgets.TextField(name='expire_in_days', label=_(u'Expire In Days'),
            help_text=_(u'Number of days after which jobs will expire'))
    needs_product = widgets.CheckBox('needs_product', label=u'Needs Product')

    tag_form = HorizontalForm(
        'Retention Tag',
        fields = [tag, default, expire_in_days, needs_product, id],
        action = 'save_data',
        submit_text = _(u'Save'),
    )

    def __init__(self,*args,**kw):
        kw['search_url'] =  url("/retentiontag/by_tag")
        kw['search_name'] = 'tag'
        kw['widget_action'] = './admin'
        super(RetentionTag,self).__init__(*args,**kw)

        self.search_col = Tag.tag
        self.search_mapper = Tag 

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.tag_form,
            action = './save',
            options = {},
            value = kw,
        )

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(form=tag_form, validators=TagFormSchema())
    @error_handler(new)
    def save(self, id=None, **kw):
        retention_tag = Tag(tag=kw['tag'], default=kw['default'],
                needs_product=kw['needs_product'],
                expire_in_days=kw['expire_in_days'])
        session.add(retention_tag)
        flash(_(u"OK"))
        redirect("./admin")

    @expose(format='json')
    def by_tag(self, input, *args, **kw):
        input = input.lower()
        search = Tag.list_by_tag(input)
        tags = [match.tag for match in search]
        return dict(matches=tags)

    @expose(template="bkr.server.templates.admin_grid")
    @identity.require(identity.in_group('admin'))
    @paginate('list', default_order='tag', limit=20)
    def admin(self, *args, **kw):
        tags = self.process_search(*args, **kw)
        alpha_nav_data = set([elem.tag[0].capitalize() for elem in tags])
        nav_bar = self._build_nav_bar(alpha_nav_data,'tag')
        template_data = self.tags(tags, identity.current.user, *args, **kw)
        template_data['alpha_nav_bar'] = nav_bar
        template_data['addable'] = True
        return template_data

    @identity.require(identity.in_group('admin'))
    @expose()
    def delete(self, id):
        tag = Tag.by_id(id)
        if not tag.can_delete(): # Trying to be funny...
            flash(u'%s is not applicable for deletion' % tag.tag)
            redirect('/retentiontag/admin')
        session.delete(tag)
        flash(u'Successfully deleted %s' % tag.tag)
        redirect('/retentiontag/admin')

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def edit(self, id, **kw):
        tag = Tag.by_id(id) 
        return dict(
            form = self.tag_form,
            title=_(u'Retention tag %s' % tag.tag),
            action = './save_edit',
            options = {},
            value = tag,
            disabled_fields = ['tag']
        )

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(form=tag_form, validators=TagFormSchema())
    @error_handler(edit)
    def save_edit(self, id=None, **kw):
        retention_tag = Tag.by_id(id)
        retention_tag.tag = kw['tag']
        retention_tag.default = kw['default']
        retention_tag.expire_in_days = kw['expire_in_days']
        retention_tag.needs_product = kw['needs_product']
        flash(_(u"OK"))
        redirect("./admin")

    @expose(template="bkr.server.templates.grid")
    @paginate('list', default_order='tag', limit=20)
    def index(self, *args, **kw):
        return self.tags()

    def tags(self, tags=None, user=None, *args, **kw):
        if tags is None:
            tags = Tag.get_all()

        def show_delete(x):
            if x.can_delete():
                return XML('<a class="btn" href="./delete/%s">'
                        '<i class="fa fa-times"/> Delete</a>' % x.id)
            else:
                return None

        def show_tag(x):
            if x.is_default: #If we are the default, we can't change to not default
                return x.tag
            elif user and user.is_admin():
                return make_edit_link(x.tag,x.id)
            else:  #no perms to edit
                return x.tag

        my_fields = [myPaginateDataGrid.Column(name='tag', title='Tags', getter=lambda x: show_tag(x),options=dict(sortable=True)),
                     myPaginateDataGrid.Column(name='default', title='Default', getter=lambda x: x.default,options=dict(sortable=True)),
                     myPaginateDataGrid.Column(name='delete', title='Delete', getter=lambda x: show_delete(x))]
        tag_grid = myPaginateDataGrid(fields=my_fields, add_action='./new')
        return_dict = dict(title='Tags',
                           grid = tag_grid,
                           search_bar = None,
                           search_widget = self.search_widget_form,
                           list = tags)
        return return_dict
