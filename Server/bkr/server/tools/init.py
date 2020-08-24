# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
import datetime
import re
import logging
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import create_session
from sqlalchemy.orm.exc import NoResultFound
from bkr.common import __version__
from bkr.log import log_to_stream, log_to_syslog
from bkr.server.model import (User, Group, Permission, Hypervisor, KernelType,
                              Arch, PowerType, Key, RetentionTag, ConfigItem, UserGroup,
                              DataMigration)
from bkr.server.util import load_config_or_exit, log_traceback
from turbogears.database import session, metadata as tg_metadata
from optparse import OptionParser
import alembic.config, alembic.script, alembic.environment
import errno
import daemon
from daemon.pidfile import PIDLockFile

__description__ = 'Command line tool for initializing Beaker DB'

PIDFILE = '/var/run/beaker-init.pid'

logger = logging.getLogger(__name__)


def check_db(metadata, target_version):
    """
    Returns True if the current database schema version matches the target
    version (does not need any upgrades/downgrades).
    """
    env_context = create_alembic_env_context(metadata)
    with metadata.bind.connect() as connection:
        env_context.configure(connection=connection, target_metadata=metadata)
        current = env_context.get_context().get_current_revision()
        target_version = beaker_version_to_schema_version(target_version)
        target = env_context.script.get_revision(target_version).revision
    if current != target:
        logger.info('Current schema %s does not match target revision %s', current, target)
        return False
    return True


def init_db(metadata):
    logger.info('Creating tables in empty database')
    if metadata != tg_metadata:
        metadata.tables = tg_metadata.tables.copy()
    metadata.create_all()

    logger.info('Stamping database with Alembic "head" revision')

    def stamp(rev, context):
        try:
            return context.script._stamp_revs('head', rev)
        except AttributeError:  # alembic < 0.7
            current = context._current_rev()
            head = context.script.get_revision('head')
            context._update_current_rev(current, head.revision)
            return []

    run_alembic_operation(metadata, stamp)

    # Also mark all data migrations as done, because there is no data to
    # migrate. This avoids beakerd wasting time trying to run them all when it
    # first starts up.
    session = create_session(bind=metadata.bind)
    with session.begin():
        for migration_name in DataMigration.all_names():
            logger.info('Marking data migration %s finished', migration_name)
            session.add(DataMigration(name=migration_name,
                                      finish_time=datetime.datetime.utcnow()))


def populate_db(user_name=None, password=None, user_display_name=None,
                user_email_address=None):
    logger.info('Populating tables with pre-defined values if necessary')
    session.begin()

    try:
        admin = Group.by_name(u'admin')
    except InvalidRequestError:
        admin = Group(group_name=u'admin', display_name=u'Admin')
        session.add(admin)

    try:
        lab_controller = Group.by_name(u'lab_controller')
    except InvalidRequestError:
        lab_controller = Group(group_name=u'lab_controller',
                               display_name=u'Lab Controller')
        session.add(lab_controller)

    # Setup User account
    if user_name:
        user = User.lazy_create(user_name=user_name.decode('utf8'))
        if password:
            user.password = password.decode('utf8')
        if user_display_name:
            user.display_name = user_display_name.decode('utf8')
        if user_email_address:
            user.email_address = user_email_address.decode('utf8')
        # Ensure the user is in the 'admin' group as an owner.
        # Flush for lazy_create.
        session.flush()
        user_group_assoc = UserGroup.lazy_create(
            user_id=user.user_id, group_id=admin.group_id)
        user_group_assoc.is_owner = True

    # Create distro_expire perm if not present
    try:
        _ = Permission.by_name(u'distro_expire')
    except NoResultFound:
        distro_expire_perm = Permission(u'distro_expire')
        session.add(distro_expire_perm)

    # Create proxy_auth perm if not present
    try:
        _ = Permission.by_name(u'proxy_auth')
    except NoResultFound:
        proxy_auth_perm = Permission(u'proxy_auth')
        session.add(proxy_auth_perm)

    # Create tag_distro perm if not present
    try:
        _ = Permission.by_name(u'tag_distro')
    except NoResultFound:
        tag_distro_perm = Permission(u'tag_distro')
        admin.permissions.append(tag_distro_perm)

    # Create stop_task perm if not present
    try:
        _ = Permission.by_name(u'stop_task')
    except NoResultFound:
        stop_task_perm = Permission(u'stop_task')
        lab_controller.permissions.append(stop_task_perm)
        admin.permissions.append(stop_task_perm)

    # Create secret_visible perm if not present
    try:
        _ = Permission.by_name(u'secret_visible')
    except NoResultFound:
        secret_visible_perm = Permission(u'secret_visible')
        lab_controller.permissions.append(secret_visible_perm)
        admin.permissions.append(secret_visible_perm)

    # Create change_prio perm if not present
    try:
        _ = Permission.by_name(u'change_prio')
    except NoResultFound:
        change_prio_perm = Permission(u'change_prio')
        session.add(change_prio_perm)

    # Setup Hypervisors Table
    if Hypervisor.query.count() == 0:
        for h in [u'KVM', u'Xen', u'HyperV', u'VMWare']:
            session.add(Hypervisor(hypervisor=h))

    # Setup kernel_type Table
    if KernelType.query.count() == 0:
        for type in [u'default', u'highbank', u'imx', u'omap', u'tegra']:
            session.add(KernelType(kernel_type=type, uboot=False))
        for type in [u'mvebu']:
            session.add(KernelType(kernel_type=type, uboot=True))

    # Setup base Architectures
    if Arch.query.count() == 0:
        for arch in [u'i386', u'x86_64', u'ia64', u'ppc', u'ppc64', u'ppc64le',
                     u's390', u's390x', u'armhfp', u'aarch64', u'arm']:
            session.add(Arch(arch))

    # Setup base power types
    if PowerType.query.count() == 0:
        for power_type in [u'apc_snmp', u'apc_snmp_then_etherwake',
                           u'bladecenter', u'bladepap', u'drac', u'ether_wake', u'hyper-v',
                           u'ilo', u'integrity', u'ipmilan', u'ipmitool', u'lpar', u'rsa',
                           u'virsh', u'wti']:
            session.add(PowerType(power_type))

    # Setup key types
    if Key.query.count() == 0:
        session.add(Key(u'DISKSPACE', True))
        session.add(Key(u'COMMENT'))
        session.add(Key(u'CPUFAMILY', True))
        session.add(Key(u'CPUFLAGS'))
        session.add(Key(u'CPUMODEL'))
        session.add(Key(u'CPUMODELNUMBER', True))
        session.add(Key(u'CPUSPEED', True))
        session.add(Key(u'CPUVENDOR'))
        session.add(Key(u'DISK', True))
        session.add(Key(u'FORMFACTOR'))
        session.add(Key(u'HVM'))
        session.add(Key(u'MEMORY', True))
        session.add(Key(u'MODEL'))
        session.add(Key(u'MODULE'))
        session.add(Key(u'NETWORK'))
        session.add(Key(u'NR_DISKS', True))
        session.add(Key(u'NR_ETH', True))
        session.add(Key(u'NR_IB', True))
        session.add(Key(u'PCIID'))
        session.add(Key(u'PROCESSORS', True))
        session.add(Key(u'RTCERT'))
        session.add(Key(u'SCRATCH'))
        session.add(Key(u'STORAGE'))
        session.add(Key(u'USBID'))
        session.add(Key(u'VENDOR'))
        session.add(Key(u'XENCERT'))
        session.add(Key(u'NETBOOT_METHOD'))

    if RetentionTag.query.count() == 0:
        session.add(RetentionTag(tag=u'scratch', is_default=1, expire_in_days=30))
        session.add(RetentionTag(tag=u'60days', needs_product=False, expire_in_days=60))
        session.add(RetentionTag(tag=u'120days', needs_product=False, expire_in_days=120))
        session.add(RetentionTag(tag=u'active', needs_product=True))
        session.add(RetentionTag(tag=u'audit', needs_product=True))

    config_items = [
        # name, description, numeric
        (u'root_password', u'Plaintext root password for provisioned systems', False),
        (u'root_password_validity', u"Maximum number of days a user's root password is valid for",
         True),
        (u'guest_name_prefix', u'Prefix for names of dynamic guests in OpenStack', False),
        (u'guest_private_network', u'Network address in CIDR format for private networks'
                                   ' of dynamic guests in OpenStack.', False),
    ]
    for name, description, numeric in config_items:
        ConfigItem.lazy_create(name=name, description=description, numeric=numeric)
    if ConfigItem.by_name(u'root_password').current_value() is None:
        ConfigItem.by_name(u'root_password').set(u'beaker', user=admin.users[0])
    if ConfigItem.by_name(u'guest_private_network').current_value() is None:
        ConfigItem.by_name(u'guest_private_network').set(u'192.168.10.0/24',
                                                         user=admin.users[0])

    session.commit()
    session.close()
    logger.info('Pre-defined values populated')


def upgrade_db(metadata):
    logger.info('Upgrading schema to head revision')

    def upgrade(rev, context):
        # In alembic 0.7, rev could be an empty set.
        if not rev:
            # This means the database is not stamped. Normally Alembic treats
            # that as the "base" revision (for us that's Beaker 0.11) but
            # actually the db could be anything from 0.11 to 0.18 (or even
            # earlier, though we refuse to handle that). We can check for some
            # indicative tables/columns to figure out what the current version
            # really is.
            logger.info('Database has no Alembic version, '
                        'inspecting schema to determine current version')
            inspector = inspect(context.bind)
            table_names = inspector.get_table_names()
            if 'recipe_reservation' in table_names:
                rev = '431e4e2ccbba'  # 0.17/0.18
            elif any(col['name'] == 'name' for col in
                     inspector.get_columns('recipe_task')):
                rev = '2f38ab976d17'  # 0.16
            elif 'system_access_policy' in table_names:
                rev = '49a4a1e3779a'  # 0.15
            elif 'submission_delegate' in table_names:
                rev = '057b088bfb32'  # 0.14
            elif any(col['name'] == 'ldap' for col in
                     inspector.get_columns('tg_group')):
                rev = '41aa3372239e'  # 0.13
            elif 'disk' in table_names:
                rev = '442672570b8f'  # 0.12
            elif any(col['name'] == 'rebooted' for col in
                     inspector.get_columns('recipe_resource')):
                rev = None  # 0.11 (base)
            else:
                raise RuntimeError('Database has no Alembic version and '
                                   'is not recognised as a valid Beaker 0.11-0.18 schema '
                                   '(you must manually migrate old databases '
                                   'up to 0.11 before running beaker-init)')
            logger.info('Treating unstamped database as version %s' % rev)
            try:
                context._update_current_rev(None, rev)
            except AttributeError:
                # In alembic 0.7, we donnot need to stamp.
                pass
        return context.script._upgrade_revs('head', rev)

    run_alembic_operation(metadata, upgrade)
    logger.info('Upgrade completed')


def beaker_version_to_schema_version(version):
    # This table is also part of the docs, ensure they stay in sync!
    #   Doc: beaker/documentation/admin-guide/upgrading.rst
    #
    # Get schema ID (alembic version identifier) with commands:
    #   cd ~/beaker/Server/bkr/server/alembic/versions
    #   git log -n 1 --stat -- .
    # And use the prefix of the file that changed
    beaker_versions = {
        '28': '4b3a6065eba2',
        '27': '4cddc14ab090',
        '26': '348daa35773c',
        '25': '1ce53a2af0ed',
        '24': 'f18df089261',
        '23': '2e171e6198e6',
        '22': '54395adc8646',
        '21': '171c07fb4970',
        '20': '19d89d5fbde6',
        '19': '53942581687f',
        '0.18': '431e4e2ccbba',
        '0.17': '431e4e2ccbba',
        '0.16': '2f38ab976d17',
        '0.15': '49a4a1e3779a',
        '0.14': '057b088bfb32',
        '0.13': '41aa3372239e',
        '0.12': '442672570b8f',
    }
    if version in beaker_versions:
        return beaker_versions[version]
    # Try to map arbitrary versions or RPM version-releases to the matching
    # major version number.
    m = re.match(r'((0\.)?\d+)\.\d.*', version)
    if m and m.group(1) in beaker_versions:
        return beaker_versions[m.group(1)]
    # Assume it's already a schema version, Alembic will tell us if it's not.
    return version


def downgrade_db(metadata, version):
    version = beaker_version_to_schema_version(version)
    logger.info('Downgrading schema to version %s', version)

    def downgrade(rev, context):
        return context.script._downgrade_revs(version, rev)

    run_alembic_operation(metadata, downgrade)
    logger.info('Downgrade completed')


def create_alembic_env_context(metadata, func=None):
    config = alembic.config.Config()
    config.set_main_option('script_location', 'bkr.server:alembic')
    script = alembic.script.ScriptDirectory.from_config(config)
    return alembic.environment.EnvironmentContext(config=config,
                                                  script=script, fn=func)


def run_alembic_operation(metadata, func):
    # We intentionally *don't* run inside the normal Alembic env.py so that we
    # can force the use of the SA metadata we are given, rather than using the
    # normal global TurboGears metadata instance. Ultimately this is to make
    # the migration testable.
    env_context = create_alembic_env_context(metadata, func)
    with metadata.bind.connect() as connection:
        env_context.configure(connection=connection, target_metadata=metadata)
        env_context.run_migrations()


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,
                          version=__version__)

    ## Actions
    parser.add_option("-c", "--config", action="store", type="string",
                      dest="configfile", help="location of config file.")
    parser.add_option("-u", "--user", action="store", type="string",
                      dest="user_name", help="username of Admin account")
    parser.add_option("-p", "--password", action="store", type="string",
                      dest="password", help="password of Admin account")
    parser.add_option("-e", "--email", action="store", type="string",
                      dest="email_address",
                      help="email address of Admin account")
    parser.add_option("-n", "--fullname", action="store", type="string",
                      dest="display_name", help="Full name of Admin account")
    parser.add_option("--downgrade", type="string", metavar='VERSION',
                      help="Downgrade database to a previous version "
                           "(accepts a schema version identifier or Beaker version)")
    parser.add_option('--check', action='store_true',
                      help='Instead of performing upgrades, only check if upgrades are necessary '
                           '(exit status is 1 if the schema is empty or not up to date)')
    parser.add_option('--debug', action='store_true',
                      help='Show detailed progress information')
    parser.add_option('--background', action='store_true',
                      help='Detach from the terminal, send messages to syslog')
    return parser


def process_is_alive(pid):
    try:
        process_name = open('/proc/%s/comm' % pid).read().strip()
    except (IOError, OSError) as e:
        if e.errno == errno.ENOENT:
            return False
        else:
            raise
    if process_name != 'beaker-init':
        return False
    return True


def main():
    parser = get_parser()
    opts, args = parser.parse_args()
    load_config_or_exit(opts.configfile)
    if opts.check and opts.background:
        parser.error('--check --background makes no sense, how will you know the result?')
    if not opts.background:
        log_to_stream(sys.stderr, level=logging.DEBUG if opts.debug else logging.WARNING)
        return doit(opts)
    else:
        pidlockfile = PIDLockFile(PIDFILE)
        existing_pid = pidlockfile.read_pid()
        if existing_pid:
            if process_is_alive(existing_pid):
                sys.stderr.write('Another beaker-init process is running (pid %s)\n'
                                 % existing_pid)
                return 1
            else:
                sys.stderr.write('Pid file %s exists but pid %s is dead, '
                                 'removing the pid file\n' % (PIDFILE, existing_pid))
                pidlockfile.break_lock()
        with daemon.DaemonContext(pidfile=pidlockfile, detach_process=True):
            log_to_syslog('beaker-init')
            return doit(opts)


@log_traceback(logger)
def doit(opts, metadata=None):
    if not metadata:
        from turbogears.database import metadata, bind_metadata
        bind_metadata()

    if opts.check:
        version = opts.downgrade or 'head'
        return 0 if check_db(metadata, version) else 1
    elif opts.downgrade:
        downgrade_db(metadata, opts.downgrade)
    else:
        table_names = metadata.bind.table_names()
        # if database is empty then initialize it
        # python-alembic-0.6.5-3 will autocreate the alembic_version table
        # when checking an empty database. This is fixed in newer alembic
        # versions; 0.8.3-4 does not have this issue
        database_is_empty = len(table_names) == 0
        only_has_alembic_version_table = (
                    len(table_names) == 1 and table_names[0] == 'alembic_version')
        if database_is_empty or only_has_alembic_version_table:
            if not opts.user_name:
                logger.error('Database is empty, you must pass --user to create an admin user')
                return 1
            init_db(metadata)
        else:
            # upgrade to the latest DB version
            upgrade_db(metadata)
        populate_db(opts.user_name, opts.password, opts.display_name, opts.email_address)
    logger.info('Exiting')
    return 0


if __name__ == "__main__":
    sys.exit(main())
