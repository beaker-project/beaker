# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from twisted.web import xmlrpc, server
from twisted.internet import reactor, protocol, stdio
from twisted.protocols import basic
from twisted.internet.defer import Deferred
import simplejson as json
import os
import os.path
import tempfile
import exceptions
import traceback
import uuid
import logging
import random
from beah.core import event, command
from beah.misc import format_exc, runtimes, make_log_handler
from beah.wires.internals.twmisc import serveAnyChild, serveAnyRequest, JSONProtocol
from beah.core.constants import RC

LOG_PATH = '/tmp/var/log'
VAR_PATH = '/var/beah'
RUNTIME_PATHNAME_TEMPLATE = VAR_PATH + '/rhts_task_%s.db'

log = logging.getLogger('rhts_task')

USE_DEFAULT = object()

################################################################################
# AUXILIARY:
################################################################################
__RESULT_RHTS_TO_BEAH = {
        "pass": RC.PASS,
        "warn": RC.WARNING,
        "fail": RC.FAIL,
        "crit": RC.CRITICAL,
        "fata": RC.FATAL,
        "pani": RC.FATAL,
        }
def result_rhts_to_beah(result):
    """Translate result codes from RHTS to beah."""
    return __RESULT_RHTS_TO_BEAH.get(result.lower()[:4], RC.WARNING)

################################################################################
# CONTROLLER LINK:
################################################################################
class ControllerLink(JSONProtocol):

    from os import linesep as delimiter

    def __init__(self, main):
        self.main = main

    def connectionMade(self):
        self.main.controller_connected()

    def proc_input(self, obj):
        try:
            self.main.controller_input(obj)
        except:
            self.main.send_evt(event.lose_item(format_exc()))

    def connectionLost(self, reason):
        self.main.controller_disconnected(reason)


################################################################################
# PROCESS:
################################################################################
class RHTSTask(protocol.ProcessProtocol):

    def __init__(self, main):
        self.main = main

    def outReceived(self, data):
        self.main.task_stdout(data)

    def errReceived(self, data):
        self.main.task_stderr(data)

    def processExited(self, reason):
        self.main.task_exited(reason)

    def processEnded(self, reason):
        self.main.task_ended(reason)


################################################################################
# XML-RPC HANDLERS:
################################################################################
class RHTSResults(xmlrpc.XMLRPC):

    def __init__(self, main):
        self.main = main

    def xmlrpc_result(self, test_name, parent_string, result, result_value,
            test_version, recipe_test_id):
        log.debug("XMLRPC: results.result(%r, %r, %r, %r, %r, %r)",
                test_name, parent_string, result, result_value, test_version,
                recipe_test_id)
        evt = event.result_ex(
                result_rhts_to_beah(result),
                handle=test_name,
                message='(%s)' % result,
                statistics={'score':result_value},
                test_version=test_version,
                recipe_test_id=recipe_test_id)
        self.main.send_evt(evt)
        return evt.id()
    xmlrpc_result.signature = [
            ['string', 'string', 'string', 'string', 'string', 'string', 'int'],
            ]

    def get_file(self, pretty_name, size=None, digest=None):
        file_id = self.main.get_file(pretty_name)
        if file_id is None:
            file_id = self.main.set_file(pretty_name)
            if file_id is None:
                return None
            evt = event.file_meta(file_id, size=size, digest=("md5", digest),
                    codec="base64")
            self.main.send_evt(evt)
        return file_id

    def xmlrpc_uploadFile(self, recipe_test_id, name, size, digest, offset,
            data):
        log.debug("XMLRPC: results.uploadFile(%r, %r, %r, %r, %r, %r)",
                recipe_test_id, name, size, digest, offset, data)
        file_id = self.get_file(name, size=size, digest=digest)
        if file_id is None:
            msg = "%s:xmlrpc_uploadFile: " % self.__class__.__name__ + \
                    "Can not create file '%s'." % name
            self.main.error(msg)
            return msg
        if offset < 0:
            evt = event.file_close(file_id)
            self.main.send_evt(evt)
            return 0
        if data:
            # FIXME: is chunk's digest necessary?
            evt = event.file_write(file_id, data, offset=offset)
            self.main.send_evt(evt)
        return 0 # or "Failure reason"
    xmlrpc_uploadFile.signature = [
            ['int', 'int', 'string', 'int', 'int', 'int', 'string'],
            ]

    def xmlrpc_resultLog(self, log_type, result_id, pretty_name):
        log.debug("XMLRPC: results.resultLog(%r, %r, %r)", log_type,
            result_id, pretty_name)
        file_id = self.get_file(pretty_name)
        if file_id is None:
            msg = "%s:xmlrpc_resultLog: " % self.__class__.__name__ + \
                    "Can not create file '%s'." % pretty_name
            self.main.error(msg)
            return msg
        id_len = len(result_id)
        if pretty_name[:id_len] == result_id:
            pretty_name = pretty_name[id_len+1:]
        evt = event.file_meta(file_id, name=pretty_name, handle=log_type)
        self.main.send_evt(evt)
        evt = event.relation('result_file', result_id, file_id)
        self.main.send_evt(evt)
        return 0 # or "Failure reason"
    xmlrpc_resultLog.signature = [
            ['int', 'string', 'int', 'string'],
            ]

    def xmlrpc_recipeTestRpms(self, test_id, pkg_list):
        log.debug("XMLRPC: results.recipeTestRpms(%r, %r)",
                test_id, pkg_list)
        # FIXME! implement this!!!
        return 0 # or "Failure reason"
    xmlrpc_recipeTestRpms.signature = [
            ['int', 'int', 'list'],
            ]


class RHTSWatchdog(xmlrpc.XMLRPC):

    def __init__(self, main):
        self.main = main

    def xmlrpc_abortJob(self, job_id):
        log.debug("XMLRPC: watchdog.abortJob(%r)", job_id)
        # FIXME: implement this
        return 0 # or "Failure reason"
    xmlrpc_abortJob.signature = [['int', 'int']]

    def xmlrpc_abortRecipeSet(self, recipe_set_id):
        log.debug("XMLRPC: watchdog.abortRecipeSet(%r)", recipe_set_id)
        # FIXME: implement this
        return 0 # or "Failure reason"
    xmlrpc_abortRecipeSet.signature = [['int', 'int']]

    def xmlrpc_abortRecipe(self, recipe_id):
        log.debug("XMLRPC: watchdog.abortRecipe(%r)", recipe_id)
        # FIXME: implement this
        return 0 # or "Failure reason"
    xmlrpc_abortRecipe.signature = [['int', 'int']]

    def xmlrpc_testCheckin(self, hostname, job_id, test, kill_time, test_id):
        log.debug("XMLRPC: watchdog.testCheckin(%r, %r, %r, %r, %r)", hostname, job_id, test, kill_time, test_id)
        # FIXME: implement this
        return 1 # or "Failure reason"
    xmlrpc_testCheckin.signature = [['int', 'string', 'int', 'string', 'int', 'int']]



class RHTSWorkflows(xmlrpc.XMLRPC):

    def __init__(self, main):
        self.main = main

    def xmlrpc_add_comment_to_recipe(self, submitter, recipe_id, comment):
        log.debug("XMLRPC: workflows.add_comment_to_recipe(%r, %r, %r)",
                submitter, recipe_id, comment)
        # FIXME: implement this...
        return 0 # or "Failure reason"


class RHTSTest(xmlrpc.XMLRPC):

    def __init__(self, main):
        self.main = main

    def xmlrpc_testCheckin(self, test_id, call_type):
        log.debug("XMLRPC: test.testCheckin(%r, %r)", test_id, call_type)
        # FIXME: implement this!!!
        return 0 # or "Failure reason"
    xmlrpc_testCheckin.signature = [['int', 'int', 'string']]


class RHTSSync(xmlrpc.XMLRPC):

    def __init__(self, main):
        self.main = main

    def trhostname(hostname):
        if hostname == os.environ['HOSTNAME']:
            return ''
        return hostname
    trhostname = staticmethod(trhostname)

    def xmlrpc_set(self, recipe_set_id, test_order, result_server, hostname,
            state):
        log.debug("XMLRPC: sync.set(%r, %r, %r, %r, %r)", recipe_set_id,
                test_order, result_server, hostname, state)
        evt = event.variable_set('sync/recipe_set_%s/test_order_%s' \
                % (recipe_set_id, test_order),
                state, dest=self.trhostname(hostname))
        self.main.send_evt(evt)
        return 0 # or "Failure reason"
    xmlrpc_set.signature = [['int', 'int', 'int', 'string', 'string', 'string']]

    def xmlrpc_block(self, recipe_set_id, test_order, result_server, states,
            hostnames):
        log.debug("XMLRPC: sync.block(%r, %r, %r, %r, %r)", recipe_set_id,
                test_order, result_server, states, hostnames)
        answ = []
        wait_for = []
        for hostname in hostnames:
            name = 'sync/recipe_set_%s/test_order_%s' \
                    % (recipe_set_id, test_order)
            dest = self.trhostname(hostname)
            evt = event.variable_get(name, dest=dest)
            self.main.send_evt(evt)
            wait_for.append((name, '', dest))
        return self.main.wait_for_variables(wait_for, states)
    xmlrpc_block.signature = [['list', 'int', 'int', 'string', 'list', 'list']]


class RHTSHandler(xmlrpc.XMLRPC):

    """A root XML-RPC handler.

    It does handle only unhandled calls. Other calls should be handled by
    subhandlers."""

    def __init__(self, main, *args, **kwargs):
        self.main = main
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        self.putSubHandler('sync', RHTSSync(main))
        self.putSubHandler('workflows', RHTSWorkflows(main))
        self.putSubHandler('watchdog', RHTSWatchdog(main))
        self.putSubHandler('results', RHTSResults(main))
        self.putSubHandler('test', RHTSTest(main))
        xmlrpc.addIntrospection(self)

    def catch_xmlrpc(self, method, *args):
        """Handler for unhandled requests."""
        log.error("ERROR: Missing method: %s%r", method, args)
        #raise xmlrpc.Fault(123, "Undefined procedure %s." % method)
        self.main.send_evt(event.output(("ERROR: UNHANDLED RPC" , method, args),
            out_handle='xmlrpc'))
        return "Error: Server can not handle command %s" % method

serveAnyChild(RHTSHandler)
serveAnyRequest(RHTSHandler, 'catch_xmlrpc', xmlrpc.XMLRPC)

class RHTSServer(server.Site):

    def __init__(self, main, logPath=None, timeout=60 * 60 * 12):
        self.main = main
        self.handler = RHTSHandler(main)
        server.Site.__init__(self, self.handler, logPath=logPath, timeout=timeout)

    def startFactory(self):
        server.Site.startFactory(self)
        # FIXME: waiting for server would be better:
        # - e.g. send a request and wait until it is served...
        self.main.server_started()


################################################################################
# MAIN:
################################################################################
class RHTSMain(object):

    VARIABLE_VALUE_TIMEOUT=2

    def __init__(self, task_path, env):
        self.process = None
        self.listener = None
        self.task_path = task_path
        self.__done = False
        self.__waits_for = []

        # FIXME: randomize port(?) - use configurable range of ports.
        port = os.environ.get('RHTS_PORT', random.randint(7080, 7099))

        # FIXME: is inheriting the whole environment desirable?
        if env is not USE_DEFAULT:
            self.env = dict(env)
        else:
            self.env = dict(os.environ)

        # FIXME: Any other env.variables to set?
        # FIXME: What values should be used here?
        # - some values could be received from LC when task is scheduled, but
        #   it would create a dependency!
        #   - let's use fake values, and let the Backend translate it (if
        #     supported)
        #     - e.g. JOBID, RECIPESETID, RECIPEID are not interesting at all
        #     - use task_id for RECIPESETID, and BE (or LC eventually) should
        #       be able to find about the rest...
        # RESULT_SERVER - host:port[/prefixpath]
        self.env['RESULT_SERVER'] = "%s:%s%s" % ("localhost", port, "")
        self.env.setdefault('TESTORDER', '123') # FIXME: More sensible default

        taskid = "J%(JOBID)s-S%(RECIPESETID)s-R%(RECIPEID)s-T%(TASKID)s" % self.env

        # FIXME: change log level to WARNING, use tempfile and upload log when
        # process ends.
        log = logging.getLogger('rhts_task')
        make_log_handler(log, LOG_PATH, "rhts_task_%s.log" % (taskid,))
        log.setLevel(logging.DEBUG)

        # No point in storing everything in one big file. Use one file per task
        self.__files = runtimes.TypeDict(runtimes.ShelveRuntime(RUNTIME_PATHNAME_TEMPLATE % taskid), 'vars')

        # FIXME: should any checks go here?
        # e.g. does Makefile PURPOSE exist? try running `make testinfo.desc`? ...

        self.controller = ControllerLink(self)
        self.task = RHTSTask(self)
        self.server = RHTSServer(self)
        # FIXME: is return value of any use?
        stdio.StandardIO(self.controller)
        # FIXME: is return value of any use?
        reactor.listenTCP(port, self.server, interface='localhost')

    def on_exit(self):
        # FIXME! handling!
        # should submit captured files (AVC_ERROR, OUTPUTFILE)
        log.info("quitting...")
        reactor.callLater(2, reactor.stop)
        self.__done = True

    def __controller_output(self, data):
        self.controller.sendLine(data)

    def send_evt(self, evt):
        log.debug("sending evt: %r", evt)
        self.__controller_output(json.dumps(evt))

    TEST_RUNNER = 'rhts-test-runner.sh'
    def server_started(self):
        # FIXME: Install rhts-test-runner.sh somewhere!
        self.process = reactor.callLater(2, reactor.spawnProcess, self.task,
                self.TEST_RUNNER,
                args=[self.TEST_RUNNER],
                env=self.env, path=self.env.get('TESTPATH', '/tmp'))


    def controller_input(self, cmd):
        # FIXME: process commands on input
        # - allowed commands: sync-set, sync-block, kill
        # - anything else?
        cmd = command.command(cmd)
        log.debug("received cmd: %r", cmd)
        if cmd.command() == 'variable_value':
            self.handle_variable_value(cmd)

    def controller_connected(self):
        pass

    def controller_disconnected(self, reason):
        if not self.__done:
            log.error("Connection to controller was lost! reason=%s", reason)
            self.on_exit()

    def task_stdout(self, data):
        # FIXME: RHTS Task can send an event! Handle it!
        self.send_evt(event.stdout(data))

    def task_stderr(self, data):
        # FIXME: RHTS Task can send an event! Handle it!
        self.send_evt(event.stderr(data))

    def task_exited(self, reason):
        if not self.__done:
            log.info("task_exited(%s)", reason)
            self.send_evt(event.linfo("task_exited", reason=str(reason)))
            self.on_exit()

    def task_ended(self, reason):
        if not self.__done:
            log.info("task_ended(%s)", reason)
            self.send_evt(event.linfo("task_ended", reason=str(reason)))
            self.on_exit()

    def handle_variable_value(self, cmd):
        log.debug("handling variable_value.")
        log.debug("...waiting for: %r", self.__waits_for)
        cmd_name = cmd.arg('key')
        cmd_handle = cmd.arg('handle')
        cmd_dest = cmd.arg('dest')
        cmd_value = cmd.arg('value')
        for ix, waits in enumerate(self.__waits_for):
            if not waits:
                continue
            (d, states, variables, dc) = waits
            answ = []
            for var in variables:
                (name, handle, dest, val) = var
                if name==cmd_name and handle==cmd_handle and dest==cmd_dest:
                    var[3] = cmd_value
                    log.debug("variable match: %r", var)
                if answ is not None:
                    if cmd_value in states:
                        log.debug("value match: %r", cmd_value)
                        answ.append(cmd_value)
                    else:
                        answ = None
            if answ is not None:
                log.debug("all values match: %r", answ)
                dc.cancel()
                d.callback(answ)
                self.__waits_for[ix] = None
        log.debug("variable_value handled.")
        log.debug("...waiting for: %r", self.__waits_for)
        self.__waits_for = list([waits for waits in self.__waits_for if waits])
        log.debug("list cleaned.")
        log.debug("...waiting for: %r", self.__waits_for)

    def wait_for_variables(self, variables, states):
        d = Deferred()
        dc = reactor.callLater(self.VARIABLE_VALUE_TIMEOUT, self.cancel_waiting, d)
        vs = [[name, handle, dest, None] for (name, handle, dest) in variables]
        self.__waits_for.append([d, states, list(vs), dc])
        return d

    def cancel_waiting(self, d):
        cancel = False
        for ix, waits in enumerate(self.__waits_for):
            if not waits:
                continue
            (dd, states, variables, dc) = waits
            if dd is d:
                self.__waits_for[ix] = None
                cancel = True
        if cancel:
            self.__waits_for = list([waits for waits in self.__waits_for if waits])
            d.errback("Timeout")
            return True
        return False

    def set_file(self, name):
        if name is None:
            return None
        if self.get_file(name) is not None:
            self.error("File '%s' already exists!" % name)
            return None
        evt = event.file(name=name)
        id = evt.id()
        self.__files[name] = id
        self.send_evt(evt)
        return id

    def get_file(self, name):
        return self.__files.get(name, None)

    def error(msg):
        log.error(msg)
        evt = event.error(message=msg)
        self.send_evt(evt)


def main(task_path=None):
    from sys import argv
    if task_path is None:
        if len(argv) > 1:
            task_path = argv[1]
        #else:
        #    log.error("Test directory not provided.", reason)
        #    raise exceptions.RuntimeError("Test directory not provided.")
    RHTSMain(task_path, USE_DEFAULT)
    reactor.run()


################################################################################
# MAIN:
################################################################################
if __name__ == '__main__':
    main()

