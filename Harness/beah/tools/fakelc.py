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

from twisted.web import xmlrpc
from twisted.internet import reactor
import beah
from beah.wires.internals.twmisc import serveAnyChild, serveAnyRequest
from beah.misc import format_exc, log_this, log_flush
import sys
import os
import exceptions
import traceback
import pprint
from random import randint
import logging

def logger():
    log = logging.getLogger('fakelc')
    lh = logging.FileHandler('/var/log/beah_fakelc.log')
    log.addHandler(lh)
    log.setLevel(logging.DEBUG)
    return log
log = logger()

# FIXME: Use config option for log_on:
print_this = log_this.log_this(lambda s: log.debug(s), log_on=True)

recipes = {}
fqdn_recipes = {}
task_recipe = {}
fqdn_def_recipe = None
task_def_recipe = None

def get_recipe_(fqdn=None, id=None, task_id=None):
    log.info("get_recipe_(fqdn=%s, id=%s, task_id=%s)", fqdn, id, task_id)
    if fqdn is not None:
        id = build_recipe(fqdn)
    if task_id is not None:
        task_id = int(task_id)
        if task_recipe.has_key(task_id):
            id = task_recipe[task_id]
        else:
            id = task_def_recipe
    if id is None:
        return None
    id = int(id)
    if recipes.has_key(id):
        return recipes[id]
    return None

def get_recipe_xml(**kwargs):
    rec = get_recipe_(**kwargs)
    if not rec:
        return None
    return rec[0] % rec[1]

def get_recipe_args(**kwargs):
    rec = get_recipe_(**kwargs)
    if not rec:
        return None
    return rec[1]

RESULT_TYPE_ = ["Pass", "Warn", "Fail", "Panic"]

def print_(obj):
    log.info("%s", obj)
    return obj

def do_get_recipe(fname, fqdn):
    log.info("%s(fqdn=%r)", fname, fqdn)
    return print_(get_recipe_xml(fqdn=fqdn))

def do_task_start(fname, task_id, kill_time):
    log.info("%s(task_id=%r, kill_time=%r)", fname, task_id, kill_time)
    rec_args = get_recipe_args(task_id=task_id)
    if not rec_args:
        return "ERROR: no task %s" % task_id
    rec_args['task%s_stat' % task_id]='Running'
    log_flush(log)
    return 0

def do_task_stop(fname, task_id, stop_type, msg):
    """
    Stop a task

    stop_type -- 'Stop'|'Abort'|'Cancel'

    return 0 on success, error message otherwise
    """
    log.info("%s(task_id=%r, stop_type=%r, msg=%r)", fname, task_id, stop_type,
            msg)
    rec_args = get_recipe_args(task_id=task_id)
    if not rec_args:
        return "ERROR: no task %s" % task_id
    rec_args['task%s_stat' % task_id]=stop_type
    log_flush(log)
    return 0

def do_task_result(fname, task_id, result_type, path, score, summary):
    """
    Report task result

    result_type -- 'Pass'|'Warn'|'Fail'|'Panic'

    return 0 on success, error message otherwise
    """
    try:
        log.info(
                "%s(task_id=%r, result_type=%r, path=%r, score=%r, summary=%r)",
                fname, task_id, result_type, path, score, summary)
        rec_args = get_recipe_args(task_id=task_id)
        if not rec_args:
            return "ERROR: no task %s" % task_id
        ix = 'task%s_res' % task_id
        result = rec_args.get(ix, "Pass")
        if RESULT_TYPE_.count(result) == 0 \
            or (RESULT_TYPE_.count(result_type) > 0 \
                    and RESULT_TYPE_.find(result) < RESULT_TYPE_.find(result_type)):
            rec_args[ix]=result_type
        answ = randint(1, 9999999)
        log.info("%s.RETURN: %s", fname, answ)
        log_flush(log)
        return answ
    except:
        log.error("%s", format_exc())
        raise

def do_task_upload_file(fname, task_id, path, name, size, digest, offset, data):
    log.info("%s(task_id=%r, path=%r, name=%r, size=%r, digest=%r, offset=%r, data='...')",
            fname, task_id, path, name, size, digest, offset)
    return 0

def do_result_upload_file(fname, result_id, path, name, size, digest, offset, data):
    log.info("%s(result_id=%r, path=%r, name=%r, size=%r, digest=%r, offset=%r, data='...')",
            fname, result_id, path, name, size, digest, offset)
    return 0

################################################################################
# XML-RPC HANDLERS:
################################################################################
class LCRecipes(xmlrpc.XMLRPC):
    def return_recipe(**kwargs):
        return get_recipe_xml(**kwargs)
    return_recipe = staticmethod(return_recipe)

    def xmlrpc_to_xml(self, recipe_id):
        log.info("recipes.to_xml(%r)", recipe_id)
        return self.return_recipe(id=recipe_id)

    def xmlrpc_system_xml(self, fqdn):
        #return self.return_recipe(fqdn=fqdn)
        return do_get_recipe("recipes.system_xml", fqdn)

class LCRecipeTasks(xmlrpc.XMLRPC):

    def xmlrpc_Start(self, task_id, kill_time):
        return do_task_start("recipes.tasks.Start", task_id, kill_time)

    def xmlrpc_Stop(self, task_id, stop_type, msg):
        return do_task_stop("recipes.tasks.Stop", task_id, stop_type, msg)

    def xmlrpc_Result(self, task_id, result_type, path, score, summary):
        return do_task_result("recipes.tasks.Result", task_id, result_type,
                path, score, summary)

class LCHandler(xmlrpc.XMLRPC):

    """XMLRPC handler to handle requests to LC."""

    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        recipes = LCRecipes()
        recipes.putSubHandler('tasks', LCRecipeTasks())
        self.putSubHandler('recipes', recipes)

    def xmlrpc_get_recipe(self, fqdn):
        return do_get_recipe("get_recipe", fqdn)

    def xmlrpc_task_start(self, task_id, kill_time):
        return do_task_start("task_start", task_id, kill_time)

    def xmlrpc_task_stop(self, task_id, stop_type, msg):
        return do_task_stop("task_stop", task_id, stop_type, msg)

    def xmlrpc_task_result(self, task_id, result_type, path, score, summary):
        return do_task_result("task_result", task_id, result_type, path, score,
                summary)

    def xmlrpc_task_upload_file(self, task_id, path, name, size, digest,
            offset, data):
        return do_task_upload_file("task_upload_file", task_id, path, name,
                size, digest, offset, data)

    def xmlrpc_result_upload_file(self, result_id, path, name, size, digest,
            offset, data):
        return do_result_upload_file("result_upload_file", result_id, path, name,
                size, digest, offset, data)

    def catch_xmlrpc(self, method, *args):
        """Handler for unhandled requests."""
        log.error("Missing method: %r", [method] + list(args))
        # This is likely to break the test, but it does not matter now...
        return "--- ERROR: Server can not handle command %s" % method

serveAnyChild(LCHandler)
serveAnyRequest(LCHandler, 'catch_xmlrpc', xmlrpc.XMLRPC)

################################################################################
# RECIPE DEFINITIONS:
################################################################################
def build_recipe(fqdn):
    if fqdn is None:
        return None
    if fqdn_recipes.has_key(fqdn):
        return fqdn_recipes[fqdn]
    return build_recipe_21(fqdn)

def build_recipe_21(fqdn):
    recipe21 = """\
            <recipe arch="i386" distro="RHEL5-Server-U3"
                    family="RedHatEnterpriseLinuxServer5"
                    status="Running" variant="None"
                    id="21" job_id="11" recipe_set_id="11"
                    system="%(machine0)s"
                    >
                <repos>
                    <repo name="beaker-task"
                            url="http://beaker-devel.app.eng.bos.redhat.com/rpms" />
                </repos>
                <distroRequires>
                    <distro_arch op="=" value="i386"/>
                    <distro_family op="=" value="RedHatEnterpriseLinuxServer5"/>
                </distroRequires>
                <hostRequires>
                    <system_type value="Machine"/>
                </hostRequires>

                <!--
                <task avg_time="1200" id="41"
                        name="/examples/testargs" role="STANDALONE"
                        result="%(task41_res)s"
                        status="%(task41_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <rpm name="rh-tests-examples-testargs-1.1-1.noarch.rpm"/>
                </task>
                            <system value="%(machine1)s"/>
                -->

                <task avg_time="1200" id="42"
                        name="/examples/testargs" role="CLIENTS"
                        result="%(task42_res)s"
                        status="%(task42_stat)s"
                        >
                    <roles>
                        <role value="CLIENTS">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <params>
                        <param name="KERNELARGNAME" value="kernel"/>
                        <param name="KERNELARGVARIANT" value="up"/>
                        <param name="KERNELARGVERSION"
                            value="2.6.18-153.el5testabort"/>
                    </params>
                    <rpm name="rh-tests-examples-testargs.noarch"/>
                </task>
                        <role value="SERVERS">
                            <system value="%(machine1)s"/>
                        </role>

                <!--
                <task avg_time="1200" id="43"
                        name="/beah/examples/tasks/a_task" role="STANDALONE"
                        result="%(task43_res)s"
                        status="%(task43_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <executable url="%(beah_root)s/examples/tasks/a_task"/>
                </task>
                            <system value="%(machine1)s"/>

                <task avg_time="1200" id="44"
                        name="/beah/examples/tasks/socket" role="STANDALONE"
                        result="%(task44_res)s"
                        status="%(task44_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <executable url="%(beah_root)s/examples/tasks/socket"/>
                </task>
                            <system value="%(machine1)s"/>

                <task avg_time="1200" id="45"
                        name="/beah/examples/tasks/rhts" role="STANDALONE"
                        result="%(task45_res)s"
                        status="%(task45_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <executable url="%(beah_root)s/examples/tasks/rhts" />
                </task>
                            <system value="%(machine1)s"/>

                <task avg_time="1200" id="46"
                        name="/beah/examples/tests/rhtsex" role="STANDALONE"
                        result="%(task46_res)s"
                        status="%(task46_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <executable url="/usr/bin/python2.6">
                        <arg value="%(beah_py_root)s/tasks/rhts_xmlrpc.py" />
                        <arg value="%(beah_root)s/examples/tests/rhtsex" />
                    </executable>
                </task>
                            <system value="%(machine1)s"/>

                <task avg_time="1200" id="47"
                        name="/beah/examples/tests/testargs" role="STANDALONE"
                        result="%(task47_res)s"
                        status="%(task47_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <executable url="/usr/bin/python2.6">
                        <arg value="%(beah_py_root)s/tasks/rhts_xmlrpc.py" />
                        <arg value="%(beah_root)s/examples/tests/testargs" />
                    </executable>
                </task>
                            <system value="%(machine1)s"/>
                -->

                <!--
                        name="/distribution/install" role="STANDALONE"
                        name="/distribution/kernelinstall" role="CLIENTS"

                <task avg_time="120" id="95" testorder="95"
                        name="/examples/rhts_tutorial/mcsontos/beah_logs" role="CLIENTS"
                        result="%(task95_res)s"
                        status="%(task95_stat)s"
                        >
                    <roles>
                        <role value="CLIENTS">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <rpm name="tmp-examples-rhts_tutorial-mcsontos-beah_logs.noarch"/>
                </task>
                -->

                <task avg_time="84400" id="99"
                        name="/examples/rhts_tutorial/mcsontos/beah_reserve" role="CLIENTS"
                        result="%(task99_res)s"
                        status="%(task99_stat)s"
                        >
                    <roles>
                        <role value="CLIENTS">
                            <system value="%(machine0)s"/>
                        </role>
                    </roles>
                    <params>
                        <param name="TESTORDER" value="99"/>
                    </params>
                    <rpm name="rh-tests-examples-rhts_tutorial-mcsontos-beah_reserve.noarch"/>
                </task>

            </recipe>
        """

    args21 = dict(
            beah_root=os.environ.get("BEAH_ROOT", None) or sys.prefix + "/share/beah",
            beah_py_root=beah.__path__[0],
            )

    global recipes, task_recipe, fqdn_recipes
    recipes[21] = (recipe21, args21)
    args = args21
    tasks = [41, 42, 43, 44, 45, 46, 47, 95, 99]
    machines = [
            fqdn or os.environ["HOSTNAME"],
            "test1.example.com",
            "lab-machine2.example.com",
            ]
    for task in tasks:
        task_recipe[task] = 21
        args['task%d_stat' % task] = 'Waiting'
        args['task%d_res' % task] = 'None'
    for machine_ix in range(len(machines)):
        machine = machines[machine_ix]
        fqdn_recipes[machine] = 21
        args['machine%d' % machine_ix] = machine
        args['machine%d_stat' % machine_ix] = 'None'

    log.info("%s", pprint.pformat(recipes))

    return 21

def main():
################################################################################
# EXECUTE:
################################################################################
    from twisted.web import server
    lc = LCHandler()
    s = server.Site(LCHandler(), None, 60*60*12)
    #reactor.listenTCP(5222, s, interface='localhost')
    reactor.listenTCP(5222, s)
    reactor.run()

################################################################################
# RUN:
################################################################################
if __name__ == '__main__':
    main()

