# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import signal
import sys
from datetime import datetime
from optparse import OptionParser

import daemon
import gevent
import gevent.event
import gevent.monkey
import gevent.pool
import gevent.pywsgi
from daemon import pidfile
from flask.wrappers import Request, Response
from six.moves.xmlrpc_server import SimpleXMLRPCDispatcher
from werkzeug.exceptions import (
    BadRequest,
    HTTPException,
    MethodNotAllowed,
    RequestEntityTooLarge,
)
from werkzeug.routing import Map as RoutingMap
from werkzeug.routing import Rule

from bkr.common.helpers import RepeatTimer
from bkr.labcontroller.config import get_conf, load_conf
from bkr.labcontroller.proxy import Proxy, ProxyHTTP
from bkr.log import log_to_stream, log_to_syslog

try:
    from xmlrpc.server import XMLRPCDocGenerator
except ImportError:
    from DocXMLRPCServer import XMLRPCDocGenerator

logger = logging.getLogger(__name__)


class XMLRPCDispatcher(SimpleXMLRPCDispatcher, XMLRPCDocGenerator):
    def __init__(self):
        SimpleXMLRPCDispatcher.__init__(self, allow_none=True)
        XMLRPCDocGenerator.__init__(self)

    def _dispatch(self, method, params):
        """
        Custom _dispatch so we can log exceptions and the time taken to
        execute each method.
        """
        start = datetime.utcnow()
        try:
            result = SimpleXMLRPCDispatcher._dispatch(self, method, params)
        except:
            logger.exception("Error handling XML-RPC call %s", str(method))
            logger.debug(
                "Time: %s %s %s",
                datetime.utcnow() - start,
                str(method),
                str(params)[0:50],
            )
            raise
        logger.debug(
            "Time: %s %s %s", datetime.utcnow() - start, str(method), str(params)[0:50]
        )
        return result


class LimitedRequest(Request):
    max_content_length = 10 * 1024 * 1024  # 10MB


class WSGIApplication(object):
    def __init__(self, proxy):
        self.proxy = proxy
        self.proxy_http = ProxyHTTP(proxy)
        self.xmlrpc_dispatcher = XMLRPCDispatcher()
        self.xmlrpc_dispatcher.register_instance(proxy)
        self.url_map = RoutingMap(
            [
                # pseudo-XML-RPC calls used in kickstarts:
                # (these permit GET to make it more convenient to trigger them using curl)
                Rule("/nopxe/<fqdn>", endpoint=(self.proxy, "clear_netboot")),
                Rule(
                    "/install_start/<recipe_id>", endpoint=(self.proxy, "install_start")
                ),
                Rule(
                    "/install_done/<recipe_id>/", endpoint=(self.proxy, "install_done")
                ),
                Rule(
                    "/install_done/<recipe_id>/<fqdn>",
                    endpoint=(self.proxy, "install_done"),
                ),
                Rule(
                    "/postinstall_done/<recipe_id>",
                    endpoint=(self.proxy, "postinstall_done"),
                ),
                Rule("/postreboot/<recipe_id>", endpoint=(self.proxy, "postreboot")),
                Rule(
                    "/install_fail/<recipe_id>/", endpoint=(self.proxy, "install_fail")
                ),
                # Harness API:
                Rule(
                    "/recipes/<recipe_id>/",
                    methods=["GET"],
                    endpoint=(self.proxy_http, "get_recipe"),
                ),
                Rule(
                    "/recipes/<recipe_id>/watchdog",
                    methods=["GET"],
                    endpoint=(self.proxy_http, "get_watchdog"),
                ),
                Rule(
                    "/recipes/<recipe_id>/watchdog",
                    methods=["POST"],
                    endpoint=(self.proxy_http, "post_watchdog"),
                ),
                Rule(
                    "/recipes/<recipe_id>/status",
                    methods=["POST"],
                    endpoint=(self.proxy_http, "post_recipe_status"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/",
                    methods=["PATCH"],
                    endpoint=(self.proxy_http, "patch_task"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/status",
                    methods=["POST"],
                    endpoint=(self.proxy_http, "post_task_status"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/results/",
                    methods=["POST"],
                    endpoint=(self.proxy_http, "post_result"),
                ),
                Rule(
                    "/recipes/<recipe_id>/logs/",
                    methods=["GET"],
                    endpoint=(self.proxy_http, "list_recipe_logs"),
                ),
                Rule(
                    "/recipes/<recipe_id>/logs/<path:path>",
                    methods=["GET", "PUT"],
                    endpoint=(self.proxy_http, "do_recipe_log"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/logs/",
                    methods=["GET"],
                    endpoint=(self.proxy_http, "list_task_logs"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/logs/<path:path>",
                    methods=["GET", "PUT"],
                    endpoint=(self.proxy_http, "do_task_log"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/results/<result_id>/logs/",
                    methods=["GET"],
                    endpoint=(self.proxy_http, "list_result_logs"),
                ),
                Rule(
                    "/recipes/<recipe_id>/tasks/<task_id>/results/<result_id>/logs/<path:path>",
                    methods=["GET", "PUT"],
                    endpoint=(self.proxy_http, "do_result_log"),
                ),
                Rule(
                    "/power/<fqdn>/",
                    methods=["PUT"],
                    endpoint=(self.proxy_http, "put_power"),
                ),
                Rule(
                    "/healthz/",
                    methods=["HEAD", "GET"],
                    endpoint=(self.proxy_http, "healthz"),
                ),
            ]
        )

    @LimitedRequest.application
    def __call__(self, req):
        try:
            # Limit request data in all cases.
            if (
                req.max_content_length is not None
                and req.content_length > req.max_content_length
            ):
                raise RequestEntityTooLarge()
            if req.path in ("/", "/RPC2", "/server"):
                if req.method == "POST":
                    # XML-RPC
                    if req.mimetype != "text/xml":
                        return BadRequest("XML-RPC requests must be text/xml")
                    result = self.xmlrpc_dispatcher._marshaled_dispatch(req.data)
                    return Response(response=result, content_type="text/xml")
                elif req.method in ("GET", "HEAD"):
                    # XML-RPC docs
                    return Response(
                        response=self.xmlrpc_dispatcher.generate_html_documentation(),
                        content_type="text/html",
                    )
                else:
                    return MethodNotAllowed()
            else:
                (obj, attr), args = self.url_map.bind_to_environ(req.environ).match()
                if obj is self.proxy:
                    # pseudo-XML-RPC
                    result = getattr(obj, attr)(**args)
                    return Response(response=repr(result), content_type="text/plain")
                else:
                    return getattr(obj, attr)(req, **args)
        except HTTPException as e:
            return e


# Temporary hack to disable keepalive in gevent.wsgi.WSGIServer. This should be easier.
class WSGIHandler(gevent.pywsgi.WSGIHandler):
    def read_request(self, raw_requestline):
        result = super(WSGIHandler, self).read_request(raw_requestline)
        self.close_connection = True
        return result


# decorator to log uncaught exceptions in the WSGI application
def log_failed_requests(func):
    def _log_failed_requests(environ, start_response):
        try:
            return func(environ, start_response)
        except Exception as e:
            logger.exception(
                "Error handling request %s %s",
                environ.get("REQUEST_METHOD"),
                environ.get("PATH_INFO"),
            )
            raise

    return _log_failed_requests


def daemon_shutdown(signum, frame):
    logger.info("Received signal %s, shutting down", signum)
    shutting_down.set()


def main_loop(proxy=None, conf=None):
    """infinite daemon loop"""
    global shutting_down
    shutting_down = gevent.event.Event()
    gevent.monkey.patch_all()

    # define custom signal handlers
    signal.signal(signal.SIGINT, daemon_shutdown)
    signal.signal(signal.SIGTERM, daemon_shutdown)

    login = RepeatTimer(
        conf["RENEW_SESSION_INTERVAL"], proxy.hub._login, stop_on_exception=False
    )
    login.daemon = True
    login.start()

    server = gevent.pywsgi.WSGIServer(
        ("::", 8000),
        log_failed_requests(WSGIApplication(proxy)),
        handler_class=WSGIHandler,
        spawn=gevent.pool.Pool(),
    )
    server.stop_timeout = None
    server.start()

    try:
        shutting_down.wait()
    finally:
        server.stop()
        login.stop()


def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", help="Full path to config file to use")
    parser.add_option(
        "-f",
        "--foreground",
        default=False,
        action="store_true",
        help="run in foreground (do not spawn a daemon)",
    )
    parser.add_option("-p", "--pid-file", help="specify a pid file")
    (opts, args) = parser.parse_args()

    if opts.config:
        load_conf(opts.config)
    conf = get_conf()
    logging.getLogger().setLevel(logging.DEBUG)

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get(
            "PROXY_PID_FILE", "/var/run/beaker-lab-controller/beaker-proxy.pid"
        )

    # HubProxy will try to log some stuff, even though we
    # haven't configured our logging handlers yet. So we send logs to stderr
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        proxy = Proxy(conf=conf)
    except Exception as ex:
        sys.stderr.write("Error starting beaker-proxy: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(proxy=proxy, conf=conf)
    else:
        # See BZ#977269
        proxy.close()
        with daemon.DaemonContext(
            pidfile=pidfile.TimeoutPIDLockFile(pid_file, acquire_timeout=0),
            detach_process=True,
            stderr=sys.stderr,
        ):
            log_to_syslog("beaker-proxy")
            main_loop(proxy=proxy, conf=conf)


if __name__ == "__main__":
    main()
