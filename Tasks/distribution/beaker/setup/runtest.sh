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

# Assume the test will fail.
result=FAIL

# Helper functions
# control where to log debug messages to:
# devnull = 1 : log to /dev/null
# devnull = 0 : log to file specified in ${DEBUGLOG}
devnull=0

# Create debug log
DEBUGLOG=`mktemp -p /mnt/testarea -t DeBug.XXXXXX`

# locking to avoid races
lck=$OUTPUTDIR/$(basename $0).lck

# Log a message to the ${DEBUGLOG} or to /dev/null
function DeBug ()
{
    local msg="$1"
    local timestamp=$(date '+%F %T')
    if [ "$devnull" = "0" ];then
	lockfile -r 1 $lck
	if [ "$?" = "0" ];then
	    echo -n "${timestamp}: " >>$DEBUGLOG 2>&1
	    echo "${msg}" >>$DEBUGLOG 2>&1
	    rm -f $lck >/dev/null 2>&1
	fi
    else
	echo "${msg}" >/dev/null 2>&1
    fi
}

function SubmitLog ()
{
    LOG=$1
    rhts_submit_log -S $RESULT_SERVER -T $TESTID -l $LOG
}

function result_fail()
{
    echo "***** End of runtest.sh *****" | tee -a $OUTPUTFILE
    report_result $TEST FAIL 1
    SubmitLog $DEBUGLOG
    CleanUp
    exit 0
}

function result_pass ()
{
    echo "***** End of runtest.sh *****" | tee -a $OUTPUTFILE
    report_result $TEST PASS 0
    CleanUp
    exit 0
}

function BuildBeaker ()
{
    yum install -y TurboGears python-setuptools-devel python-devel
    git clone git://git.fedorahosted.org/beaker
    pushd beaker
    make snaparchive
    make rpm
    popd
}

function InstallInventory_git()
{
    BuildBeaker
    yum install --nogpg -y  /rpmbuild/RPMS/noarch/beaker-server-*.rpm
}

function InstallInventory_repo()
{
    yum install -y beaker-server$VERSION
}

function InstallLabController_git()
{
    BuildBeaker
    yum install --nogpg -y /rpmbuild/RPMS/noarch/beaker-lab-controller-*.rpm
}

function InstallLabController_repo()
{
    yum install -y beaker-lab-controller$VERSION
}

function CleanUp ()
{
    echo "no clean up method yet"
}

#Function below will report if a prev command failed
function estatus_fail()
{
    if [ "$?" -ne "0" ];then
	DeBug "$1 Failed"
	echo "***** "$1" Failed: *****" | tee -a $OUTPUTFILE
        rhts-sync-set -s ABORT
	result_fail
    fi
}

function generate_rsync_cfg()
{
    mkdir -p /var/www/html/beaker-logs
    chown nobody /var/www/html/beaker-logs
    chmod 755 /var/www/html/beaker-logs
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

function generate_beaker_cfg()
{
    cat << __EOF__ > /etc/beaker/server.cfg
[global]
# This is where all of your settings go for your production environment.
# You'll copy this file over to your production server and provide it
# as a command-line option to your start script.
# Settings that are the same for both development and production
# (such as template engine, encodings, etc.) all go in 
# beaker/server/config/app.cfg

# DATABASE

# pick the form for your database
# sqlobject.dburi="postgres://username@hostname/databasename"
# sqlobject.dburi="mysql://username:password@hostname:port/databasename"
# sqlobject.dburi="sqlite:///file_name_and_path"

# If you have sqlite, here's a simple default to get you started
# in development
#sqlalchemy.dburi="sqlite:///devdata.sqlite"
sqlalchemy.dburi="mysql://beaker:beaker@localhost/beaker?charset=utf8"
sqlalchemy.pool_recycle = 3600

# File Locations
basepath.logs='/var/www/beaker/logs'
basepath.rpms='/var/www/beaker/rpms'
basepath.repos='/var/www/beaker/repos'
basepath.harness='/var/www/beaker/harness'

# if you are using a database or table type without transactions
# (MySQL default, for example), you should turn off transactions
# by prepending notrans_ on the uri
# sqlobject.dburi="notrans_mysql://username:password@hostname:port/databasename"

# for Windows users, sqlite URIs look like:
# sqlobject.dburi="sqlite:///drive_letter:/path/to/file"

# Password for installed systems

test_password='$1$rhts$ShuaoxZPm2Dr79tpoP8NE.'

##
## TurboMail settings
##
mail.on = True
mail.manager = 'immediate'
mail.transport = 'smtp'
mail.provider = 'smtp'
mail.smtp.server = '127.0.0.1:19999'

beaker_email='$SUBMITTER'
beaker.reliable_distro_tag = 'RELEASED'
beaker.motd = '/etc/beaker/motd.txt'

# Authentication

identity.provider='ldapsa'
identity.ldap.enabled=$LDAPENABLED
identity.soldapprovider.uri="ldaps://ldap.bos.redhat.com"
identity.soldapprovider.basedn="dc=redhat,dc=com"
identity.soldapprovider.autocreate=True
identity.krb_auth_principal='HTTP/$HOSTNAME@REDHAT.COM'
identity.krb_auth_keytab='/etc/httpd/conf/httpd.keytab'

# SERVER

tg.url_domain='localhost'
tg.url_scheme='http'

server.socket_port=8084
server.environment="development"
server.webpath="/bkr/"
server.log_file = "/var/log/beaker/server.log"
server.log_to_screen = True

autoreload.package="bkr.server"
tg.strict_parameters = True

# Sets the number of threads the server uses
# server.thread_pool = 1

# Set to True if you are deploying your App behind a proxy
# e.g. Apache using mod_proxy
# base_url_filter.on = False

# Set to True if your proxy adds the x_forwarded_host header
# base_url_filter.use_x_forwarded_host = True

# If your proxy does not add the x_forwarded_host header, set
# the following to the *public* host url.
# (Note: This will be overridden by the use_x_forwarded_host option
# if it is set to True and the proxy adds the header correctly.
# base_url_filter.base_url = "http://www.example.com"

[/static]
static_filter.on = True
static_filter.dir = "/usr/share/bkr/server/static"

[/favicon.ico]
static_filter.on = True
static_filter.file = "/usr/share/bkr/server/static/images/favicon.ico"

# LOGGING
# Logging configuration generally follows the style of the standard
# Python logging module configuration. Note that when specifying
# log format messages, you need to use *() for formatting variables.
# Deployment independent log configuration is in beaker/server/config/log.cfg
[logging]

[[handlers]]

[[[debug_out]]]
class='FileHandler'
formatter='full_content'
args="('/var/log/beaker/server-debug.log', 'a+')"

[[[error_out]]]
level='WARN'
class='FileHandler'
formatter='full_content'
args="('/var/log/beaker/server-errors.log', 'a+')"

[[[access_out]]]
# set the filename as the first argument below
args="('/var/log/beaker/server.log',)"
class='FileHandler'
level='INFO'
formatter='message_only'

[[loggers]]
[[[bkr.server]]]
level='DEBUG'
qualname='bkr.server'
handlers=['debug_out']

[[[access]]]
level='INFO'
handlers=['access_out', 'error_out']
__EOF__
    cat << __EOF__ > /etc/beaker/motd.txt
<span>Integration tests are running against this server</span>
__EOF__
}

function Inventory()
{
    PACKAGES="mysql-server MySQL-python python-twill"
    yum install -y $PACKAGES
    estatus_fail "**** Yum Install of $PACKAGES Failed ****"
    InstallInventory$SOURCE
    # Backup /etc/my.cnf and make INNODB the default engine.
    cp /etc/my.cnf /etc/my.cnf-orig
    cat /etc/my.cnf-orig | awk '
        {print $1};
        /\[mysqld\]/ {
            print "default-storage-engine=INNODB";
            print "max_allowed_packet=50M";
            print ENVIRON["MYSQL_EXTRA_CONFIG"];
        }' > /etc/my.cnf
    #
    service mysqld start
    estatus_fail "**** Failed to start mysqld ****"

    echo "create database beaker;" | mysql || result_fail
    echo "grant all on beaker.* to 'beaker'@'localhost' IDENTIFIED BY 'beaker';" | mysql || result_fail

    if [ -z "$LDAPENABLED" ]; then
        LDAPENABLED="False"
    fi
    # Add in Kerberos config
    generate_beaker_cfg
    mkdir -p /var/www/beaker/harness # in lieu of running beaker-repo-update

    beaker-init -u admin -p testing -e $SUBMITTER
    estatus_fail "**** Failed to initialize beaker DB ****"
    # beaker-init creates the server.log as root.  this prevents apache from 
    #  working since it can't write to it.
    /bin/rm -f /var/log/beaker/server*.log
    service iptables stop
    # Turn on wsgi
    perl -pi -e 's|^#LoadModule wsgi_module modules/mod_wsgi.so|LoadModule wsgi_module modules/mod_wsgi.so|g' /etc/httpd/conf.d/wsgi.conf
    service httpd restart
    estatus_fail "**** Failed to start httpd ****"
    service beakerd start
    estatus_fail "**** Failed to start beakerd ****"
    # Add the lab controller(s)
    for CLIENT in $CLIENTS; do
        ./add_labcontroller.py -l $CLIENT
    done
    estatus_fail "**** Failed to add lab controller ****"
    generate_rsync_cfg
    chkconfig rsync on
    rhts-sync-set -s SERVERREADY
    rhts-sync-block -s DONE -s ABORT $CLIENTS
    result_pass 
}

function LabController()
{
    # limit to only ipv4 address
    ipaddress=$(host $HOSTNAME | awk '/has address/ {print $NF}')
    yum install -y python-twill
    InstallLabController$SOURCE
    chkconfig httpd on
    chkconfig xinetd on
    chkconfig tftp on
    chkconfig cobblerd on
    #FIXME edit /etc/cobbler/settings
     perl -pi -e "s|^server: 127.0.0.1|server: $HOSTNAME|g" /etc/cobbler/settings
     perl -pi -e "s|^next_server: 127.0.0.1|next_server: $ipaddress|g" /etc/cobbler/settings
     perl -pi -e "s|^pxe_just_once: 0|pxe_just_once: 1|g" /etc/cobbler/settings
     perl -pi -e "s|^anamon_enabled: 0|anamon_enabled: 1|g" /etc/cobbler/settings
     perl -pi -e "s|^anamon_enabled: 0|anamon_enabled: 1|g" /etc/cobbler/settings
    #FIXME edit /etc/cobbler/modules.conf
    # enable testing auth module
    perl -pi -e "s|^module = authn_denyall|module = authn_testing|g" /etc/cobbler/modules.conf
    setsebool -P httpd_can_network_connect true
    semanage fcontext -a -t public_content_t "/var/lib/tftpboot/.*"
    semanage fcontext -a -t public_content_t "/var/www/cobbler/images/.*"
    # Configure beaker-proxy config
    generate_proxy_cfg
    # Turn on wsgi
    perl -pi -e 's|^#LoadModule wsgi_module modules/mod_wsgi.so|LoadModule wsgi_module modules/mod_wsgi.so|g' /etc/httpd/conf.d/wsgi.conf
    service httpd restart
    service xinetd start
    service cobblerd start
    cobbler get-loaders
    #service autofs start
    service iptables stop
    rhts-sync-set -s READY
    abort=$(rhts-sync-block -s SERVERREADY -s ABORT $SERVER)
    echo "abort=$abort"
    # We can start the proxies when our accounts have been created on the scheduler.
    service beaker-proxy start
    service beaker-watchdog start
    service beaker-transfer start
    rhts-sync-set -s DONE
    result_pass 
}

#Disable selinux
/usr/sbin/setenforce 0

if $(echo $CLIENTS | grep -q $HOSTNAME); then
    echo "Running test as Lab Controller" | tee -a $OUTPUTFILE
    TEST="$TEST/lab_controller"
    SERVER=$(echo $SERVERS | awk '{print $1}')
    SERVER_URL="https://testuser:testpassword\@$SERVER/bkr/"
    LabController
fi

if $(echo $SERVERS | grep -q $HOSTNAME); then
    echo "Running test as Inventory" | tee -a $OUTPUTFILE
    TEST="$TEST/inventory"
    Inventory
fi

if $(echo $STANDALONE | grep -q $HOSTNAME); then
    echo "Running test as both Lab Controller and Scheduler" | tee -a $OUTPUTFILE
    CLIENTS=$STANDALONE
    SERVERS=$STANDALONE
    SERVER=$(echo $SERVERS | awk '{print $1}')
    SERVER_URL="https://testuser:testpassword\@$SERVER/bkr/"
    TEST="$TEST/lab_controller" LabController &
    sleep 120
    TEST="$TEST/inventory" Inventory
fi

