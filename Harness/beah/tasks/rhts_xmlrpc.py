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


USE_DEFAULT = object()

# FIXME: this should use Task/Controller interfaces(?)

from twisted.web import xmlrpc
from twisted.internet import reactor, protocol
from beah.core import event
import simplejson as json
import os, tempfile

################################################################################
# XML-RPC HANDLERS:
################################################################################
class RHTSResults(xmlrpc.XMLRPC):
    def xmlrpc_result(self, test_name, parent_string, result, result_value,
            test_version, recipe_test_id):
        # FIXME: implement this
        print "XMLRPC: results.result(%r, %r, %r, %r, %r, %r)" % (test_name,
                parent_string, result, result_value, test_version,
                recipe_test_id)
        return 1 # result_id - used by further resultLog calls
    xmlrpc_result.signature = [
            ['int', 'string', 'string', 'string', 'string', 'string', 'int'],
            ]

    def xmlrpc_resultLog(self, log_type, result_id, pretty_name):
        # FIXME: implement this
        print "XMLRPC: results.resultLog(%r, %r, %r)" % (log_type, result_id,
                pretty_name)
        return 0 # or "Failure reason"
    xmlrpc_resultLog.signature = [
            ['int', 'string', 'int', 'string'],
            ]

    def xmlrpc_uploadFile(self, recipe_test_id, name, size, digest, offset, data):
        # FIXME: implement this
        print "XMLRPC: results.uploadFile(%r, %r, %r, %r, %r, %r)" % \
                (recipe_test_id, name, size, digest, offset, data)
        return 0 # or "Failure reason"
    xmlrpc_uploadFile.signature = [
            ['int', 'int', 'string', 'int', 'int', 'int', 'string'],
            ]


class RHTSWatchdog(xmlrpc.XMLRPC):
    def xmlrpc_abortJob(self, job_id):
        # FIXME: implement this
        print "XMLRPC: watchdog.abortJob(%r)" % (job_id)
        return 0 # or "Failure reason"
    xmlrpc_abortJob.signature = [['int', 'int']]

    def xmlrpc_abortRecipeSet(self, recipe_set_id):
        # FIXME: implement this
        print "XMLRPC: watchdog.abortRecipeSet(%r)" % (recipe_set_id)
        return 0 # or "Failure reason"
    xmlrpc_abortRecipeSet.signature = [['int', 'int']]

    def xmlrpc_abortRecipe(self, recipe_id):
        # FIXME: implement this
        print "XMLRPC: watchdog.abortRecipe(%r)" % (recipe_id)
        return 0 # or "Failure reason"
    xmlrpc_abortRecipe.signature = [['int', 'int']]


class RHTSWorkflows(xmlrpc.XMLRPC):
    def xmlrpc_add_comment_to_recipe(self, submitter, recipe_id, comment):
        # FIXME: implement this
        print "XMLRPC: workflows.add_comment_to_recipe(%r, %r, %r)" % \
                (submitter, recipe_id, comment)
        return 0 # or "Failure reason"


class RHTSSync(xmlrpc.XMLRPC):
    def xmlrpc_set(self, recipe_set_id, test_order, result_server, hostname, state):
        # FIXME: implement this!!!
        print "XMLRPC: sync.set(%r, %r, %r, %r, %r)" % (recipe_set_id,
                test_order, result_server, hostname, state)
        # Requires communication with LC
        return 0 # or "Failure reason"
    xmlrpc_set.signature = [['int', 'int', 'int', 'string', 'string', 'string']]

    def xmlrpc_block(self, recipe_set_id, test_order, result_server, states, hostnames):
        # FIXME: implement this!!!
        print "XMLRPC: sync.block(%r, %r, %r, %r, %r)" % (recipe_set_id,
                test_order, result_server, states, hostnames)
        answ = []
        for name in hostnames:
            # Requires communication with LC
            answ.append(states[0])
        return answ
    xmlrpc_block.signature = [['list', 'int', 'int', 'string', 'list', 'list']]


################################################################################
# SERVER AND TASK:
################################################################################
def serveAnyChild(cls):
    def getChild(self, path, request):
        """Will return self for any child request."""
        return self
    cls.getChild = getChild

def serveAnyRequest(cls, by, base=USE_DEFAULT):
    if base is USE_DEFAULT:
        base = cls.__base__

    if base is None:
        def _getFunction(self, functionPath):
            """Will return handler for all requests."""
            return getattr(self, by)
    else:
        def _getFunction(self, functionPath):
            """Will return handler for all unhandled requests."""
            try:
                return base._getFunction(self, functionPath)
            except:
                return getattr(self, by)
    cls._getFunction = _getFunction

class RHTSHandler(xmlrpc.XMLRPC):
    """An example object to be published."""

    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        self.putSubHandler('sync', RHTSSync())
        self.putSubHandler('workflows', RHTSWorkflows())
        self.putSubHandler('watchdog', RHTSWatchdog())
        self.putSubHandler('results', RHTSResults())
        xmlrpc.addIntrospection(self)

    def catch_xmlrpc(self, method, *args):
        """Handler for unhandled requests."""
        print >> sys.stderr, "ERROR: Missing method:", [method] + list(args)
        #raise xmlrpc.Fault(123, "Undefined procedure %s." % method)
        print json.dumps(event.output(("ERROR: UNHANDLED RPC" ,method, args), 'xmlrpc'))
        return "Error: Server can not handle command %s" % method

serveAnyChild(RHTSHandler)
serveAnyRequest(RHTSHandler, 'catch_xmlrpc', xmlrpc.XMLRPC)

class RHTSTask(protocol.ProcessProtocol):
    def __init__(self):
        pass

    def outReceived(self, data):
        # FIXME: there may be Events written to stdout
        print json.dumps(event.stdout(data))

    def errReceived(self, data):
        print json.dumps(event.stderr(data))

    def processExited(self, reason):
        # FIXME: handle this
        # should submit captured files (AVC_ERROR, OUTPUTFILE)
        print "processExited(%r)" % reason
        reactor.callLater(2, reactor.stop)

    def processEnded(self, reason):
        # FIXME: handle this
        # should submit captured files (AVC_ERROR, OUTPUTFILE)
        print "processEnded(%r)" % reason
        reactor.callLater(2, reactor.stop)


from twisted.web import server
class RHTSServer(server.Site):
    def __init__(self, task_path, env, logPath=None, timeout=60 * 60 * 12):
        self.handler = RHTSHandler()
        server.Site.__init__(self, handler, logPath=logPath, timeout=timeout)
        self.task = None
        self.task_path = task_path
        self.env = env

    def startFactory(self):
        server.Site.startFactory(self)

        # FIXME: waiting for server could have been better:
        # - e.g. send a request and wait until it is served...
        self.task = RHTSTask()
        reactor.callLater(2, reactor.spawnProcess, self.task, 'make',
                args=['make', 'run'], env=self.env, path=self.task_path)

def run_rhts_task(task_path, env=USE_DEFAULT):
    """\
Run a rhts task. It is expected to be installed in task_path already.
    
@param task_path path where task files reside
@param env       environment to execute with"""

    # FIXME: randomize port - in some (configurable) range.
    port = 7080

    if env is USE_DEFAULT:
        # FIXME: is inheriting the whole environment desirable?
        env = dict(os.environ)

    # RESULT_SERVER - host:port[/prefixpath]
    env['RESULT_SERVER'] = "%s:%s%s" % ("localhost", port, "")
    # values should be received from LC when task is scheduled(?)
    env['JOBID'] = '1'
    env['RECIPESETID'] = '1'
    env['RECIPEID'] = '1'
    env['RECIPETESTID'] = '1'
    env['TESTORDER'] = '1'
    env['OUTPUTFILE'] = tempfile.mkstemp()[1]
    env['AVC_ERROR'] = tempfile.mkstemp()[1]

    # FIXME: should any checks go here?
    # e.g. does Makefile PURPOSE exist? try running `make testinfo.desc`? ...

    reactor.listenTCP(port, RHTSServer(task_path=task_path, env=env), interface='localhost')

if __name__ == '__main__':
    # FIXME: find an appropriate test (or I will have to write one). Candidates:
    # kernel, distribution/install, sed, ruby, ImageMagick, httpd, guile, bash,
    # binutils, emacs, gcc43/candcplusplus, lynx, mysql, sendmail, sqlite,
    # squid, zsh
    run_rhts_task('/home/mcsontos/rhts/tests/examples/testargs', USE_DEFAULT)
    reactor.run()

