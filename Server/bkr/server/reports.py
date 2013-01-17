import datetime
from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, \
        error_handler, validators, redirect, paginate, url, config
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from sqlalchemy.sql import func, and_, or_, not_, select
from sqlalchemy.orm import create_session, contains_eager
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import SearchBar, myPaginateDataGrid
from bkr.server.controller_utilities import SearchOptions
from bkr.server.model import System, Reservation, SystemStatus, SystemType, \
        Arch, SystemStatusDuration, Group
from bkr.server.util import absolute_url, get_reports_engine
from bkr.server import search_utility
from distro import Distros
from bkr.server.external_reports import ExternalReportsController

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib
from turbojson import jsonify
import csv
from cStringIO import StringIO
import string
import pkg_resources
import logging

log = logging.getLogger(__name__)

def datetime_range(start, stop, step):
    dt = start
    while dt < stop:
        yield dt
        dt += step

def js_datetime(dt):
    """
    Returns the given datetime in so-called JavaScript datetime format (ms 
    since epoch).
    """
    return int(dt.strftime('%s')) * 1000 + dt.microsecond // 1000

def datetime_from_js(s):
    """
    Takes ms since epoch and returns a datetime.
    """
    if isinstance(s, basestring):
        s = float(s)
    return datetime.datetime.fromtimestamp(s / 1000)

class Reports(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
    external = ExternalReportsController()

    extension_controllers = []
    for entry_point in pkg_resources.iter_entry_points('bkr.controllers.reports'):
        controller = entry_point.load()
        log.info('Attaching reports extension controller %s as %s',
                controller, entry_point.name)
        extension_controllers.append(controller)
        locals()[entry_point.name] = controller

    @expose(template="bkr.server.templates.grid")
    @paginate('list',limit=50, default_order='start_time')
    def index(self, *args, **kw):
        return self.reserve(*args, **kw)

    def reserve(self, action='.', *args, **kw): 
        searchvalue = None 
        reserves = System.all(identity.current.user).join('open_reservation')\
                .options(contains_eager(System.open_reservation))
        reserves_return = self._reserves(reserves, **kw)
        search_options = {}
        if reserves_return:
            if 'reserves_found' in reserves_return:
                reserves = reserves_return['reserves_found']
            if 'searchvalue' in reserves_return:
                searchvalue = reserves_return['searchvalue']
            if 'simplesearch' in reserves_return:
                search_options['simplesearch'] = reserves_return['simplesearch']

        search_bar = SearchBar(name='reservesearch',
                               label=_(u'Reserve Search'),
                               table = search_utility.SystemReserve.search.create_search_table(),
                               complete_data=search_utility.SystemReserve.search.create_complete_search_table(),
                               search_controller=url("./get_search_options_reserve"),
                               )
        reservations = [system.open_reservation for system in reserves]
                               
        reserve_grid = myPaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='system.fqdn', getter=lambda x: make_link(url  = '/view/%s' % x.system.fqdn, text = x.system), title=u'System', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='start_time',
                                    getter=lambda x: x.start_time,
                                    title=u'Reserved Since',
                                    options=dict(sortable=True, datetime=True)),
                                  widgets.PaginateDataGrid.Column(name='user', getter=lambda x: x.user, title=u'Current User', options=dict(sortable=True)),
                              ])

        return dict(title=u"Reserve Report",
                    grid = reserve_grid,
                    search_bar = search_bar,
                    options = search_options,
                    action=action, 
                    searchvalue = searchvalue,
                    object_count=len(reservations),
                    list=reservations)

    def _reserves(self,reserve,**kw):
        return_dict = {} 
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['reservesearch'] = [{'table' : 'Name',   
                                   'operation' : 'contains', 
                                   'value' : kw['simplesearch']}]                    
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch}) 
        if kw.get("reservesearch"):
            searchvalue = kw['reservesearch']  
            reserves_found = self._reserve_search(reserve,**kw)
            return_dict.update({'reserves_found':reserves_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _reserve_search(self,reserve,**kw):
        reserve_search = search_utility.SystemReserve.search(reserve)
        for search in kw['reservesearch']:
            col = search['table'] 
            reserve_search.append_results(search['value'],col,search['operation'],**kw)
        return reserve_search.return_results()

    @expose(format='json')
    def get_search_options_reserve(self,table_field,**kw):
        field = table_field
        search = search_utility.SystemReserve.search.search_on(field)
        col_type = search_utility.SystemReserve.search.field_type(field)
        return SearchOptions.get_search_options_worker(search,col_type)

    @expose(template='bkr.server.templates.utilisation_graph')
    def utilisation_graph(self):
        groups = Group.query.filter(Group.system_assocs.any()).order_by(Group.group_name)
        return {
            'all_arches': [(a.id, a.arch) for a in Arch.query],
            'all_groups': [(g.group_id, g.group_name) for g in groups],
        }

    @cherrypy.expose
    @validate(validators={
        'start': validators.Wrapper(to_python=datetime_from_js),
        'end': validators.Wrapper(to_python=datetime_from_js),
        'resolution': validators.Int(),
        })
    def utilisation_timeseries(self, start=None, end=None, resolution=70,
            tg_format='json', tg_errors=None, **kwargs):
        if tg_errors:
            raise cherrypy.HTTPError(status=400, message=repr(tg_errors))
        retval = dict(manual=[], recipe=[], idle_automated=[], idle_manual=[],
                idle_broken=[], idle_removed=[])
        reports_session = create_session(bind=get_reports_engine())
        try:
            systems = self._systems_for_timeseries(reports_session, **kwargs)
            if not start:
                start = systems.value(func.min(System.date_added)) or datetime.datetime(2009, 1, 1)
            if not end:
                end = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            dts = list(dt.replace(microsecond=0) for dt in
                    datetime_range(start, end, step=(end - start) / resolution))
            for dt in dts:
                reserved_query = systems.join('reservations')\
                        .filter(and_(
                            Reservation.start_time <= dt,
                            or_(Reservation.finish_time >= dt, Reservation.finish_time == None)))\
                        .group_by(Reservation.type)\
                        .values(Reservation.type, func.count(System.id))
                reserved = dict(reserved_query)
                for reservation_type in ['recipe', 'manual']:
                    retval[reservation_type].append(reserved.get(reservation_type, 0))
                idle_query = systems\
                        .filter(System.date_added <= dt)\
                        .filter(not_(System.id.in_(select([Reservation.system_id]).where(and_(
                            Reservation.start_time <= dt,
                            or_(Reservation.finish_time >= dt, Reservation.finish_time == None))))))\
                        .join('status_durations')\
                        .filter(and_(
                            SystemStatusDuration.start_time <= dt,
                            or_(SystemStatusDuration.finish_time >= dt, SystemStatusDuration.finish_time == None)))\
                        .group_by(SystemStatusDuration.status)\
                        .values(SystemStatusDuration.status, func.count(System.id))
                idle = dict(idle_query)
                for status in SystemStatus:
                    retval['idle_%s' % status.value.lower()].append(idle.get(status, 0))
        finally:
            reports_session.close()
        if tg_format == 'json':
            cherrypy.response.headers['Content-Type'] = 'application/json'
            return jsonify.encode(dict((k, zip((js_datetime(dt) for dt in dts), v))
                    for k, v in retval.items()))
        elif tg_format == 'csv':
            cherrypy.response.headers['Content-Type'] = 'text/csv'
            stringio = StringIO()
            csv_writer = csv.writer(stringio)
            # metadata
            csv_writer.writerow(['Date generated', str(datetime.datetime.utcnow()
                    .replace(microsecond=0).isoformat()) + 'Z'])
            csv_writer.writerow(['Generated by', identity.current.user])
            csv_writer.writerow(['URL', absolute_url('/reports/utilisation_timeseries?' + cherrypy.request.query_string)])
            csv_writer.writerow([])
            # header
            csv_writer.writerow(['timestamp', 'manual', 'recipe', 'idle (automated)',
                    'idle (manual)', 'idle (broken)'])
            # data
            csv_writer.writerows(zip(dts, retval['manual'], retval['recipe'],
                    retval['idle_automated'], retval['idle_manual'], retval['idle_broken']))
            return stringio.getvalue()
        else:
            raise cherrypy.HTTPError(status=400, message='Unrecognised tg_format %r' % tg_format)

    @expose(format='json')
    def existence_timeseries(self, **kwargs):
        """
        The utilisation graphs use this data to show an "overview" graph of the 
        historical trend of system numbers. The user can select date ranges 
        from this overview. So we need to accept the same system filtering 
        params as the utilisation_timeseries method, but no date range.
        """
        reports_session = create_session(bind=get_reports_engine())
        try:
            systems = self._systems_for_timeseries(reports_session, **kwargs)
            # build a cumulative frequency type of thing
            count = 0
            cum_freqs = {}
            for date_added, in systems.values(System.date_added):
                count += 1
                cum_freqs[js_datetime(date_added.replace(hour=0, minute=0, second=0, microsecond=0))] = count
            cum_freqs[js_datetime(datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))] = count
        finally:
            reports_session.close()
        return dict(cum_freqs=sorted(cum_freqs.items()))

    def _systems_for_timeseries(self, reports_session, arch_id=[], group_id=[], only_shared=False):
        if not isinstance(arch_id, list):
            arch_id = [arch_id]
        arch_id = [int(x) for x in arch_id]
        if not isinstance(group_id, list):
            group_id = [group_id]
        group_id = [int(x) for x in group_id]
        systems = reports_session.query(System)\
                .filter(System.type == SystemType.machine)
        if arch_id:
            arch_clauses = [System.arch.any(id=x) for x in arch_id]
            systems = systems.filter(or_(*arch_clauses))
        if group_id:
            group_clauses = []
            if -1 in group_id:
                group_id.remove(-1)
                group_clauses.append(System.group_assocs == None)
            group_clauses.extend(System.group_assocs.any(group_id=x) for x in group_id)
            systems = systems.filter(or_(*group_clauses))
        if only_shared:
            systems = systems.filter(System.shared == True)
        return systems
