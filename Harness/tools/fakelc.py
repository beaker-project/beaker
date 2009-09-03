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
from beah.wires.internals.twmisc import serveAnyChild, serveAnyRequest
import os

recipes = {}
fqdn_recipes = {}
task_recipe = {}

def get_recipe(fqdn=None, id=None, task_id=None):
    print "get_recipe(fqdn=%s, id=%s)" % (fqdn, id)
    if fqdn is not None:
        if not fqdn_recipes.has_key(fqdn):
            return None
        id = fqdn_recipes[fqdn]
    if task_id is not None:
        task_id = int(task_id)
        if not task_recipe.has_key(task_id):
            return None
        id = task_recipe[task_id]
    if id is not None:
        id = int(id)
        if not recipes.has_key(id):
            return None
        return recipes[id]
    return None

def get_recipe_xml(**kwargs):
    rec = get_recipe(**kwargs)
    if not rec:
        return None
    return rec[0] % rec[1]

def get_recipe_args(**kwargs):
    rec = get_recipe(**kwargs)
    if not rec:
        return None
    return rec[1]

################################################################################
# XML-RPC HANDLERS:
################################################################################
class LCRecipes(xmlrpc.XMLRPC):
    @staticmethod
    def return_recipe(**kwargs):
        rec_xml = get_recipe_xml(**kwargs)
        if not rec_xml:
            return None
        return dict(xml = rec_xml)

    def xmlrpc_to_xml(self, recipe_id):
        return self.return_recipe(id=recipe_id)

    def xmlrpc_system_xml(self, fqdn):
        return self.return_recipe(fqdn=fqdn)

class LCRecipeTasks(xmlrpc.XMLRPC):
    result_type_ = ["Pass", "Warn", "Fail", "Panic"]
    def xmlrpc_Start(self, task_id, kill_time):
        print "tasks.Start(task_id=%r, kill_time=%r)" % (task_id, kill_time)
        rec_args = get_recipe_args(task_id=task_id)
        if not rec_args:
            return "ERROR: no task %s" % task_id
        rec_args['task%s_stat' % task_id]='Running'
        return 0
    def xmlrpc_Stop(self, task_id, stop_type, msg):
        # stop_type: Stop|Abort|Cancel
        print "tasks.Start(task_id=%r, stop_type=%r, msg=%r)" % (task_id, stop_type, msg)
        rec_args = get_recipe_args(task_id=task_id)
        if not rec_args:
            return "ERROR: no task %s" % task_id
        rec_args['task%s_stat' % task_id]=stop_type
        return 0
    def xmlrpc_Result(self, task_id, result_type, path, score, summary):
        # result_type: Pass|Warn|Fail|Panic
        print "tasks.Result(task_id=%r, result_type=%r, path=%r, score=%r, summary=%r)" % (task_id, result_type, path, score, summary)
        rec_args = get_recipe_args(task_id=task_id)
        if not rec_args:
            return "ERROR: no task %s" % task_id
        ix = 'task%s_res' % task_id
        result = rec_args[ix]
        if self.result_type_.find(result) < self.result_type_.find(result_type):
            rec_args[ix]=result_type
        return 0

class LCHandler(xmlrpc.XMLRPC):
    """An example object to be published."""

    def __init__(self, *args, **kwargs):
        xmlrpc.XMLRPC.__init__(self, *args, **kwargs)
        recipes = LCRecipes()
        recipes.putSubHandler('tasks', LCRecipeTasks())
        self.putSubHandler('recipes', recipes)

    def catch_xmlrpc(self, method, *args):
        """Handler for unhandled requests."""
        print >> sys.stderr, "ERROR: Missing method:", [method] + list(args)
        # This is likely to break the test, but it does not matter now...
        return "--- ERROR: Server can not handle command %s" % method

serveAnyChild(LCHandler)
serveAnyRequest(LCHandler, 'catch_xmlrpc', xmlrpc.XMLRPC)

################################################################################
# RUN:
################################################################################
if __name__ == '__main__':

################################################################################
# RECIPE DEFINITIONS:
################################################################################
    recipe21 = """\
            <recipe arch="i386" distro="RHEL5-Server-U3"
                    family="RedHatEnterpriseLinuxServer5"
                    status="Running" variant="None"
                    id="21" job_id="11" recipe_set_id="11"
                    system="%(machine0)s"
                    >
                <distroRequires>
                    <distro_arch op="=" value="i386"/>
                    <distro_family op="=" value="RedHatEnterpriseLinuxServer5"/>
                </distroRequires>
                <hostRequires>
                    <system_type value="Machine"/>
                </hostRequires>
                <task avg_time="1200" id="41"
                        name="/distribution/install" role="STANDALONE"
                        result="%(task41_res)s"
                        status="%(task41_stat)s"
                        >
                    <roles>
                        <role value="STANDALONE">
                            <system value="%(machine0)s"/>
                            <system value="%(machine1)s"/>
                        </role>
                    </roles>
                    <rpm name="rh-tests-examples-testargs-1.1-1.noarch.rpm"/>
                </task>
                <task avg_time="1200" id="42"
                        name="/distribution/kernelinstall" role="CLIENTS"
                        result="%(task42_res)s"
                        status="%(task42_stat)s"
                        >
                    <roles>
                        <role value="CLIENTS">
                            <system value="%(machine0)s"/>
                        </role>
                        <role value="SERVERS">
                            <system value="%(machine1)s"/>
                        </role>
                    </roles>
                    <params>
                        <param name="KERNELARGNAME" value="kernel"/>
                        <param name="KERNELARGVARIANT" value="up"/>
                        <param name="KERNELARGVERSION" value="2.6.18-153.el5testabort"/>
                    </params>
                    <rpm name="rh-tests-examples-testargs.noarch"/>
                </task>
            </recipe>
        """

    args21 = dict(
            machine0=os.environ['HOSTNAME'],
            #machine0="glen-mhor.englab.brq.redhat.com",
            machine1="dell-pe1850-01.rhts.eng.bos.redhat.com",
            machine2="hp-lp1.rhts.eng.bos.redhat.com",

            machine0_stat="None",
            machine1_stat="None",
            machine2_stat="None",

            task41_stat="Waiting",
            task42_stat="Waiting",
            task43_stat="Waiting",
            task44_stat="Waiting",

            task41_res="None",
            task42_res="None",
            task43_res="None",
            task44_res="None",
            )

    recipes[21] =(recipe21, args21)
    task_recipe[41] = 21
    task_recipe[42] = 21
    task_recipe[43] = 21
    task_recipe[44] = 21
    fqdn_recipes["glen-mhor.englab.brq.redhat.com"           ] = 21
    fqdn_recipes["localhost"                                 ] = 21
    fqdn_recipes["dell-pe1850-01.rhts.eng.bos.redhat.com"    ] = 21
    fqdn_recipes["hp-lp1.rhts.eng.bos.redhat.com"            ] = 21

################################################################################
# EXECUTE:
################################################################################
    from twisted.web import server
    lc = LCHandler()
    s = server.Site(LCHandler(), None, 60*60*12)
    reactor.listenTCP(5222, s, interface='localhost')
    reactor.run()

