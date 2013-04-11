#!/bin/sh

# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Bill Peck <bpeck@redhat.com>

# source the test script helpers
. /usr/bin/rhts-environment.sh
. /usr/share/beakerlib/beakerlib.sh

function BuildBeaker ()
{
    rlRun "git clone git://git.beaker-project.org/beaker"
    rlRun "pushd beaker"
    if [[ -n "$BEAKER_GIT_REMOTE" ]] ; then
        rlRun "git fetch $BEAKER_GIT_REMOTE ${BEAKER_GIT_REF:-master} && git checkout FETCH_HEAD"
    else
        rlRun "git checkout ${BEAKER_GIT_REF:-master}"
    fi
    rlRun "yum-builddep -y ./beaker.spec"
    rlRun "yum -y install tito"
    rlRun "tito build --rpm --test"
    rlRun "popd"
    rlRun "createrepo /tmp/tito/noarch/"
    cat >/etc/yum.repos.d/beaker-local-builds.repo <<"EOF"
[tito]
name=tito
baseurl=file:///tmp/tito/noarch/
EOF
    rlAssert0 "Created yum repo config for /tmp/tito/noarch/" $?
}

function InstallInventory_git()
{
    rlRun "yum install --nogpg -y beaker-server"
}

function InstallInventory_repo()
{
    rlRun "yum install -y beaker-server$VERSION"
}

function InstallLabController_git()
{
    rlRun "yum install --nogpg -y beaker-lab-controller beaker-lab-controller-addDistro"
}

function InstallLabController_repo()
{
    rlRun "yum install -y beaker-lab-controller$VERSION"
    rlRun "yum install -y beaker-lab-controller-addDistro$VERSION"
}

function generate_rsync_cfg()
{
    rlRun "mkdir -p /var/www/html/beaker-logs"
    rlRun "chown nobody /var/www/html/beaker-logs"
    rlRun "chmod 755 /var/www/html/beaker-logs"
    cat <<__EOF__ > /etc/rsyncd.conf
use chroot = false

[beaker-logs]
	path = /var/www/html/beaker-logs
	comment = beaker logs
	read only = false
__EOF__
}

function generate_proxy_cfg()
{
    cat << __EOF__ > /etc/beaker/labcontroller.conf
HUB_URL = "https://$SERVER/bkr/"
AUTH_METHOD = "password"
USERNAME = "host/$HOSTNAME"
PASSWORD = "testing"
CACHE = True
ARCHIVE_SERVER = "http://$SERVER/beaker-logs"
ARCHIVE_BASEPATH = "/var/www/html/beaker"
ARCHIVE_RSYNC = "rsync://$SERVER/beaker-logs"
RSYNC_FLAGS = "-arv --timeout 300"
QPID_BUS=False
__EOF__
}

function Inventory()
{
 rlJournalStart
   rlLogInfo "Starting beaker install as Inventory"
   rlPhaseStartSetup
     PACKAGES="mysql-server MySQL-python python-twill"
     rlRun "yum install -y $PACKAGES" 0
     InstallInventory$SOURCE
     # Backup /etc/my.cnf and make INNODB the default engine.
     rlRun "cp /etc/my.cnf /etc/my.cnf-orig"
     cat /etc/my.cnf-orig | awk '
         {print $1};
         /\[mysqld\]/ {
             print "default-storage-engine=INNODB";
             print "max_allowed_packet=50M";
             print "character-set-server=utf8";
             print ENVIRON["MYSQL_EXTRA_CONFIG"];
         }' > /etc/my.cnf
     #
     rlServiceStart mysqld
 
     rlRun "mysql -u root -e \"CREATE DATABASE beaker;\"" 0 "Creating database 'beaker'"
     rlRun "mysql -u root -e \"GRANT ALL ON beaker.* TO beaker@localhost IDENTIFIED BY 'beaker';\"" 0 "Granting privileges to the user 'beaker@localhost'"

     rlRun "mkdir -p /var/www/beaker/harness" 0 "in lieu of running beaker-repo-update"
     cat << __EOF__ > /etc/beaker/motd.txt
<span>Integration tests are running against this server</span>
__EOF__
     if [ -n "$IMPORT_DB" ]
     then
         rlRun "wget $IMPORT_DB" 0 "Retrieving remote DB"
         DB_FILE=echo $IMPORT_DB | perl -pe 's|.+/(.+\.xz)$|\1|'
         rlRun "xzcat $DB_FILE | mysql" 0 "Importing DB"
     else
         rlRun "beaker-init -u admin -p testing -e $SUBMITTER" 0 "Initialing DB"
     fi
     # beaker-init creates the server.log as root.  this prevents apache from 
     #  working since it can't write to it.
     rlRun "/bin/rm -f /var/log/beaker/*" 0 "Removing root owned logs"
     rlServiceStop iptables
     # Turn on wsgi
     perl -pi -e 's|^#LoadModule wsgi_module modules/mod_wsgi.so|LoadModule wsgi_module modules/mod_wsgi.so|g' /etc/httpd/conf.d/wsgi.conf
     if [ -n "$GRAPHITE_SERVER" ] ; then
        sed -i \
            -e "/^#carbon.address /c carbon.address = ('$GRAPHITE_SERVER', ${GRAPHITE_PORT:-2023})" \
            -e "/^#carbon.prefix /c carbon.prefix = '${GRAPHITE_PREFIX:+$GRAPHITE_PREFIX.}beaker.'" \
            /etc/beaker/server.cfg
     fi
     rlServiceStart httpd
     rlServiceStart beakerd
     # Add the lab controller(s)
     for CLIENT in $CLIENTS; do
         rlRun "./add-labcontroller.py -l $CLIENT" 0 "Add Lab Controller"
     done
     generate_rsync_cfg
     rlRun "chkconfig rsync on" 0 "Turn rsync on"
     if [ -n "$ENABLE_COLLECTD" ] ; then
        rlRun "yum install -y collectd"
        cat >/etc/collectd.d/beaker-server.conf <<EOF
LoadPlugin processes
LoadPlugin write_graphite
<Plugin write_graphite>
  <Carbon>
    Host "$GRAPHITE_SERVER"
    Port "${GRAPHITE_PORT:-2023}"
    Prefix "${GRAPHITE_PREFIX:+$GRAPHITE_PREFIX/}host/"
  </Carbon>
</Plugin>
<Plugin processes>
  Process "beakerd"
  Process "httpd"
</Plugin>
EOF
        rlRun "chkconfig collectd on"
        rlServiceStart collectd
     fi
     rlRun "rhts-sync-set -s SERVERREADY" 0 "Inventory ready"
     rlRun "rhts-sync-block -s DONE -s ABORT $CLIENTS" 0 "Lab Controllers ready"
   rlPhaseEnd
 rlJournalEnd
}

function LabController()
{
 rlJournalStart
   rlLogInfo "Starting beaker install as Lab Controller"
   rlPhaseStartSetup
    # limit to only ipv4 address
    ipaddress=$(host $HOSTNAME | awk '/has address/ {print $NF}')
    rlRun "yum install -y python-twill"
    InstallLabController$SOURCE
    rlRun "chkconfig httpd on"
    rlRun "chkconfig xinetd on"
    rlRun "chkconfig tftp on"
    # Configure beaker-proxy config
    generate_proxy_cfg
    # configure beaker client
    perl -pi -e 's|^#USERNAME.*|USERNAME = "admin"|' /etc/beaker/client.conf
    perl -pi -e 's|^#PASSWORD.*|PASSWORD = "testing"|' /etc/beaker/client.conf
    echo "add_distro=1" > /etc/sysconfig/beaker_lab_import
    # Turn on wsgi
    perl -pi -e 's|^#LoadModule wsgi_module modules/mod_wsgi.so|LoadModule wsgi_module modules/mod_wsgi.so|g' /etc/httpd/conf.d/wsgi.conf
    rlServiceStart httpd xinetd cobblerd
    # Using cobbler to get the netboot loaders..
    rlRun "cobbler get-loaders" 0 "get network boot loaders"
    rlRun "cobbler sync" 0 "sync boot loaders to tftpboot"
    rlServiceStop cobblerd
    rlServiceStop iptables
    rlRun "rhts-sync-set -s READY" 0 "Lab Controller ready"
    rlRun "rhts-sync-block -s SERVERREADY -s ABORT $SERVER" 0 "Wait for Server to become ready"
    rlServiceStart beaker-proxy beaker-watchdog beaker-provision
    # There is beaker-transfer as well but its disabled by default
    if [ -n "$ENABLE_BEAKER_PXEMENU" ] ; then
        rlLog "Creating beaker_pxemenu cron job"
        cat >/etc/cron.hourly/beaker_pxemenu <<"EOF"
#!/bin/bash
exec beaker-pxemenu -q
EOF
        chmod 755 /etc/cron.hourly/beaker_pxemenu
    fi
    if [ -n "$ENABLE_COLLECTD" ] ; then
        rlRun "yum install -y collectd"
        cat >/etc/collectd.d/beaker-lab-controller.conf <<EOF
LoadPlugin processes
LoadPlugin write_graphite
<Plugin write_graphite>
  <Carbon>
    Host "$GRAPHITE_SERVER"
    Port "${GRAPHITE_PORT:-2023}"
    Prefix "${GRAPHITE_PREFIX:+$GRAPHITE_PREFIX/}host/"
  </Carbon>
</Plugin>
<Plugin processes>
  Process "beaker-proxy"
  Process "beaker-provisio"
  Process "beah_dummy.py"
</Plugin>
EOF
        rlRun "chkconfig collectd on"
        rlServiceStart collectd
    fi
    rlRun "rhts-sync-set -s DONE" 0 "Lab Controller done"
   rlPhaseEnd
 rlJournalEnd
}

#Disable selinux
/usr/sbin/setenforce 0

if $(echo $CLIENTS | grep -q $HOSTNAME); then
    rlLog "RUnning as Lab Controller using Inventory: ${SERVERS}"
    TEST="$TEST/lab_controller"
    SERVER=$(echo $SERVERS | awk '{print $1}')
    [[ $SOURCE == "_git" ]] && BuildBeaker
    LabController
    rm -f /etc/yum.repos.d/beaker-local-builds.repo
    exit 0
fi

if $(echo $SERVERS | grep -q $HOSTNAME); then
    rlLog "Running as Inventory using Lab Controllers: ${CLIENTS}"
    TEST="$TEST/inventory"
    [[ $SOURCE == "_git" ]] && BuildBeaker
    Inventory
    rm -f /etc/yum.repos.d/beaker-local-builds.repo
    exit 0
fi

if [ -z "$SERVERS" -o -z "$CLIENTS" ]; then
    rlLog "Inventory=${SERVERS} LabController=${CLIENTS} Assuming Single Host Mode."
    CLIENTS=$STANDALONE
    SERVERS=$STANDALONE
    SERVER=$(echo $SERVERS | awk '{print $1}')
    [[ $SOURCE == "_git" ]] && BuildBeaker
    TEST="$TEST/lab_controller" LabController &
    sleep 120
    TEST="$TEST/inventory" Inventory
    rm -f /etc/yum.repos.d/beaker-local-builds.repo
    exit 0
fi

rlLog "JOBID=$JOBID Inventory: ${SERVERS} LabControllers: ${CLIENTS}"
rlDie "main() BUG: Return to dealer for repair!"
