
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import logging
from xmlrpc.client import loads, dumps, Fault

from flask import request, Response
from formencode.api import Invalid

from bkr.server.app import app
from bkr.server.database import session
from bkr.server import identity
from bkr.server.rpc import _NAMESPACES

log = logging.getLogger(__name__)


class XMLRPCMethodDoesNotExist(TypeError):
    pass


def _resolve(method):
    namespace, _, name = method.rpartition('.')
    obj = _NAMESPACES.get(namespace)
    func = getattr(obj, name, None)
    if obj is None or func is None or not getattr(func, 'exposed', False):
        raise XMLRPCMethodDoesNotExist(method)
    return func


@app.route('/RPC2', methods=['POST'])
@app.route('/client/', methods=['POST'])
def rpc2():
    params, method = loads(request.get_data(), use_datetime=True)
    try:
        if method == 'RPC2':
            raise AssertionError("method cannot be 'RPC2'")
        result = _resolve(method)(*params)
        body = dumps((result,), methodresponse=1, allow_none=True)
        session.flush()
    except identity.IdentityFailure as e:
        session.rollback()
        body = dumps(Fault(1, '%s: %s' % (e.__class__, e)))
    except Fault as fault:
        session.rollback()
        body = dumps(fault)
    except XMLRPCMethodDoesNotExist as e:
        session.rollback()
        body = dumps(Fault(1,
                'XML-RPC method %s not implemented by this server' % e.args[0]))
    except Invalid as e:
        session.rollback()
        body = dumps(Fault(1, str(e)))
    except Exception:
        session.rollback()
        log.exception('Error handling XML-RPC method')
        body = dumps(Fault(1, '%s:%s' % sys.exc_info()[:2]))
    return Response(body, content_type='text/xml')
