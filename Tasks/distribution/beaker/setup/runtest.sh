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

function InstallInventory()
{
    BuildBeaker
    yum install --nogpg -y  /rpmbuild/RPMS/noarch/beaker-server-*.rpm
}

function InstallLabController()
{
    BuildBeaker
    yum install --nogpg -y /rpmbuild/RPMS/noarch/beaker-lab-controller-*.rpm
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
sqlalchemy.dburi="mysql://beaker:beaker@localhost/beaker"
sqlalchemy.pool_recycle = 3600


# if you are using a database or table type without transactions
# (MySQL default, for example), you should turn off transactions
# by prepending notrans_ on the uri
# sqlobject.dburi="notrans_mysql://username:password@hostname:port/databasename"

# for Windows users, sqlite URIs look like:
# sqlobject.dburi="sqlite:///drive_letter:/path/to/file"


# Authentication

identity.provider='ldapsa'
identity.ldap.enabled=$LDAPENABLED
identity.soldapprovider.uri="ldaps://ldap.bos.redhat.com"
identity.soldapprovider.basedn="dc=redhat,dc=com"
identity.soldapprovider.autocreate=True
identity.krb_auth_principal='HTTP/$HOSTNAME@REDHAT.COM'
identity.krb_auth_keytab='/etc/httpd/conf/httpd.keytab'

# SERVER

server.socket_port=8084
server.environment="development"
server.webpath=""
server.log_file = "/var/log/beaker/server.log"
server.log_to_screen = True

autoreload.package="beaker.server"
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

tg.include_widgets = ['turbogears.mochikit']

[/static]
static_filter.on = True
static_filter.dir = "/usr/share/beaker/server/static"

[/favicon.ico]
static_filter.on = True
static_filter.file = "/usr/share/beaker/server/static/images/favicon.ico"

# LOGGING
# Logging configuration generally follows the style of the standard
# Python logging module configuration. Note that when specifying
# log format messages, you need to use *() for formatting variables.
# Deployment independent log configuration is in beaker/server/config/log.cfg
[logging]

[[handlers]]

[[[access_out]]]
# set the filename as the first argument below
args="('/var/log/beaker/server.log',)"
class='FileHandler'
level='INFO'
formatter='message_only'

[[loggers]]
[[[server]]]
level='ERROR'
qualname='beaker.server'
handlers=['error_out']

[[[access]]]
level='INFO'
qualname='turbogears.access'
handlers=['access_out']
propagate=0
__EOF__
}

function Inventory()
{
    # We only want the first one
    CLIENT=$(echo $CLIENTS| awk '{print $1}')
    PACKAGES="mysql-server MySQL-python python-twill"
    yum install -y $PACKAGES
    estatus_fail "**** Yum Install of $PACKAGES Failed ****"
    InstallInventory
    service mysqld start
    estatus_fail "**** Failed to start mysqld ****"

    echo "create database beaker;" | mysql || result_fail
    echo "grant all on beaker.* to 'beaker'@'localhost' IDENTIFIED BY 'beaker';" | mysql || result_fail

    if [ -z "$LDAPENABLED" ]; then
        LDAPENABLED="False"
    fi
    # Add in Kerberos config
    generate_beaker_cfg

    beaker-init -u admin -p testing -e $SUBMITTER
    estatus_fail "**** Failed to initialize beaker DB ****"
    # beaker-init creates the server.log as root.  this prevents apache from 
    #  working since it can't write to it.
    /bin/rm -f /var/log/beaker/server.log
    service iptables stop
    service httpd start
    estatus_fail "**** Failed to start httpd ****"
    # Add the lab controller
    ./add_labcontroller.py -l $CLIENT
    estatus_fail "**** Failed to add lab controller ****"
    rhts-sync-set -s READY
    rhts-sync-block -s DONE -s ABORT $CLIENT
    result_pass 
}

function LabController()
{
    # We only want the first one
    SERVER=$(echo $SERVERS| awk '{print $1}')
    ipaddress=$(host $HOSTNAME | awk '{print $NF}')
    yum install -y python-twill
    InstallLabController
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
     perl -pi -e "s|^redhat_management_server: .*|redhat_management_server: \"https://testuser:testpassword\@$SERVER\"|g" /etc/cobbler/settings
    #FIXME edit /etc/cobbler/modules.conf
     # enable testing auth module
     perl -pi -e "s|^module = authn_denyall|module = authn_testing|g" /etc/cobbler/modules.conf
    setsebool -P httpd_can_network_connect true
    semanage fcontext -a -t public_content_t "/var/lib/tftpboot/.*"
    semanage fcontext -a -t public_content_t "/var/www/cobbler/images/.*"
    service httpd start
    service xinetd start
    service cobblerd start
    #service autofs start
    service iptables stop
    rhts-sync-set -s READY
    abort=$(rhts-sync-block -s READY -s ABORT $SERVER)
    echo "abort=$abort"
    # Add some distros
    # NFS format HOSTNAME:DISTRONAME:NFSPATH
    if [ -z "$NFSDISTROS" ]; then
        echo "Missing NFS Distros to test with" | tee -a $OUTPUTFILE
        report_result $TEST Warn
        exit 1
    fi
    for distro in $NFSDISTROS; do
        NFSSERVER=$(echo $distro| awk -F: '{print $1}')
        DISTRONAME=$(echo $distro| awk -F: '{print $2}')
        NFSPATH=$(echo $distro| awk -F: '{print $3}')
        NFSDIR=$(dirname $NFSPATH)
        if [ ! -e "/fakenet/${NFSSERVER}${NFSDIR}" ]; then
            mkdir -p /fakenet/${NFSSERVER}${NFSDIR}
            mount ${NFSSERVER}:${NFSDIR} /fakenet/${NFSSERVER}${NFSDIR}
        fi
        cobbler import --path=/fakenet/${NFSSERVER}${NFSPATH} \
                       --name=${DISTRONAME}_nfs \
                       --available-as=nfs://${NFSSERVER}:${NFSPATH}
        report_result $TEST/ADD_DISTRO/$DISTRONAME PASS $?
    done
    /var/lib/cobbler/triggers/sync/post/osversion.trigger | tee -a $OUTPUTFILE
    estatus_fail "**** Failed to run osversion.trigger ****"
    for distro in $NFSDISTROS; do
        DISTRONAME=$(echo $distro| awk -F: '{print $2}')
        FAMILY=$(echo $distro| awk -F: '{print $4}')
        UPDATE=$(echo $distro| awk -F: '{print $5}')
        ./verify_distro.py -d $DISTRONAME -f $FAMILY -u $UPDATE -s $SERVER
        rc=$?
        if [ $rc -ne 0 ]; then
            report_result $TEST/VERIFY_DISTRO/$DISTRONAME FAIL $rc
        else
            report_result $TEST/VERIFY_DISTRO/$DISTRONAME PASS $rc
        fi
    done
    rhts-sync-set -s DONE
    result_pass 
}

if [ -z "$SERVERS" -o -z "$CLIENTS" ]; then
    echo "Can not determine my Role! Client/Server Failed:" | tee -a $OUTPUTFILE
    echo "If you are running in developer mode try setting" | tee -a $OUTPUTFILE
    echo "the environment variables CLIENTS and SERVERS"    | tee -a $OUTPUTFILE
    report_result $TEST Warn
fi

if $(echo $CLIENTS | grep -q $HOSTNAME); then
    echo "Running test as Lab Controller" | tee -a $OUTPUTFILE
    TEST="$TEST/lab_controller"
    LabController
fi

if $(echo $SERVERS | grep -q $HOSTNAME); then
    echo "Running test as Inventory" | tee -a $OUTPUTFILE
    TEST="$TEST/inventory"
    Inventory
fi

