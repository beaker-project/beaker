from turbogears import expose, url, validators, identity, validate, \
    error_handler, flash, redirect
from turbogears.database import session
from turbogears.widgets import TableForm, TextArea, TextField, HiddenField
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import DeleteLinkWidgetForm
from bkr.server.model import ExternalReport


class ExternalReportsController(RPCRoot):

    id = HiddenField(name='id')
    name = TextField(name='name', label=_(u'Report Name'),
                     attrs={'maxlength': 100},
                     validator=validators.NotEmpty())
    url = TextField(name='url', label=_(u'URL'),
                    attrs={'maxlength': 10000},
                    validator=validators.NotEmpty())
    description = TextArea(name='description',
                          label=_(u'Description'),
                          attrs={'cols': '27',
                                 'rows': '10'})
    external_report_form =TableForm(
        fields=[id, name, url, description],
        submit_text = _(u'Save'),
    )

    delete_link = DeleteLinkWidgetForm()

    @expose('bkr.server.templates.external_reports')
    def index(self):
        all_reports = ExternalReport.query.all()
        if not all_reports:
            all_reports = []
        return dict(action=url('new'),
                    delete_link= self.delete_link,
                    title='External Reports',
                    value=all_reports,)

    @identity.require(identity.in_group('admin'))
    @expose(template='bkr.server.templates.form-post')
    def new(self, **kw):
        return dict(
            form = self.external_report_form,
            action = url('save'),
            options = None,
            value = kw,
            title='New External Report',
        )

    @identity.require(identity.in_group("admin"))
    @expose('bkr.server.templates.form-post')
    def edit(self, id=None, **kw):
        return dict(form=self.external_report_form,
                     action=url('save'),
                     options={},
                     title='Edit External Report',
                     value=id and ExternalReport.by_id(id) or kw,)

    @identity.require(identity.in_group("admin"))
    @expose()
    def delete(self, id):
        report = ExternalReport.by_id(id)
        report_name = report.name
        session.delete(report)
        flash(_(u'Deleted report %s' % report_name))
        redirect('.')

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(external_report_form)
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('id'):
            report = ExternalReport.by_id(kw['id'])
        else:
            report = ExternalReport()
        report.name = kw.get('name')
        report.url = kw.get('url')
        report.description = kw.get('description')
        session.add(report)
        flash(_(u"%s saved" % report.name))
        redirect(".")
