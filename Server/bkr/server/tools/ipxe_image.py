
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in 
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

from bkr.common import __version__
__description__ = 'Generate and upload an image for iPXE booting to OpenStack Glance'

import sys
import os
from optparse import OptionParser
import logging
import socket
import tempfile
import subprocess
import datetime
import keystoneclient.v2_0.client
import glanceclient
from turbogears import config
from bkr.log import log_to_stream
from bkr.server.util import load_config_or_exit, absolute_url
from bkr.server.model import session, OpenStackRegion

log = logging.getLogger(__name__)

def _image_name():
    # Beaker doesn't actually care about the image name at all, and OpenStack 
    # doesn't require it to be unique, but we try to generate a descriptive 
    # name just to make it easier for the admin to find in Horizon.
    return 'ipxe-beaker-%s-%s' % (
            config.get('tg.url_domain', socket.getfqdn()),
            datetime.date.today().strftime('%Y%m%d'))

def generate_image():
    f = tempfile.NamedTemporaryFile(suffix='.beaker-ipxe-image')
    log.debug('Generating image in %s', f.name)
    f.truncate(4 * 1024 * 1024) # 4MB
    subprocess.check_call(['mkdosfs', f.name], stdout=open('/dev/null', 'a'))
    subprocess.check_call(['syslinux', '--install', f.name])
    subprocess.check_call(['mcopy', '-i', f.name,
            '/usr/share/ipxe/ipxe.lkrn', '::ipxe.lkrn'])
    mcopy = subprocess.Popen(['mcopy', '-i', f.name, '-', '::syslinux.cfg'],
            stdin=subprocess.PIPE)
    mcopy.communicate("""\
DEFAULT ipxe
LABEL ipxe
KERNEL ipxe.lkrn
APPEND dhcp && chain %s
""" % absolute_url('/systems/by-uuid/${uuid}/ipxe-script', scheme='http', labdomain=True))
    if mcopy.returncode != 0:
        raise RuntimeError('mcopy syslinux.cfg failed with return code %s'
                % mcopy.returncode)
    return f

def upload_image(glance):
    # For now we are just assuming there is always one region.
    region = OpenStackRegion.query.first()
    if not region:
        raise RuntimeError('No region defined in openstack_region table')
    f = generate_image()
    try:
        f.seek(0)
        image_name = _image_name()
        log.debug('Creating Glance image %s', image_name)
        image = glance.images.create(name=image_name,
                disk_format='raw', container_format='bare', is_public=True)
        log.debug('Uploading image %s to Glance', f.name)
        image.update(data=f)
        region.ipxe_image_id = image.id
    finally:
        os.unlink(f.name)

def main():
    parser = OptionParser(description=__description__, version=__version__)
    parser.add_option('-c', '--config-file')
    parser.add_option('--debug', action='store_true',
            help='Show detailed information about image creation')
    parser.add_option('--no-upload', dest='upload', action='store_false',
            help='Skip uploading to Glance, leave image temp file on disk')
    parser.add_option('--os-username', help='OpenStack username')
    parser.add_option('--os-password', help='OpenStack password')
    parser.add_option('--os-tenant-name', help='OpenStack tenant name')
    parser.set_defaults(debug=False, upload=True)
    options, args = parser.parse_args()
    load_config_or_exit(options.config_file)
    log_to_stream(sys.stderr, level=logging.DEBUG if options.debug else logging.WARNING)

    if options.upload:
        # Get a Glance client. This seems more difficult than it should be...
        username = options.os_username or os.environ.get('OS_USERNAME')
        if not username:
            parser.error('Specify username with --os-username or env[OS_USERNAME]')
        password = options.os_password or os.environ.get('OS_PASSWORD')
        if not password:
            parser.error('Specify password with --os-password or env[OS_PASSWORD]')
        tenant_name = options.os_tenant_name or os.environ.get('OS_TENANT_NAME')
        if not tenant_name:
            parser.error('Specify tenant with --os-tenant-name or env[OS_TENANT_NAME]')
        auth_url = config.get('openstack.identity_api_url')
        if not auth_url:
            parser.error('OpenStack Identity API URL is not set in the configuration')
        log.debug('Authenticating to Keystone')
        keystone = keystoneclient.v2_0.client.Client(username=username, password=password,
                tenant_name=tenant_name, auth_url=auth_url)
        log.debug('Looking up Glance URL in service catalog')
        glance_url = keystone.service_catalog.url_for(
                service_type='image', endpoint_type='publicURL')
        log.debug('Using Glance URL %s', glance_url)
        glance = glanceclient.Client('1', endpoint=glance_url, token=keystone.auth_token)
        # Generate and upload the image.
        with session.begin():
            upload_image(glance)
    else:
        print generate_image().name

if __name__ == '__main__':
    main()
