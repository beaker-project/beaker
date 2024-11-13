
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys, os

from six.moves import urllib
from six.moves import xmlrpc_client


def check_http(url):
    try:
        urllib.request.urlopen(url, timeout=120)
        return True
    except urllib.error.HTTPError as e:
        if e.code in (404, 410):
            return False
        else:
            raise


def check_ftp(url):
    try:
        urllib.request.urlopen(url, timeout=120)
        return True
    except urllib.error.URLError as e:
        if '550' in e.reason:
            return False
        else:
            raise


class NFSServerInaccessible(ValueError):
    pass


def check_nfs(tree):
    """
    Make sure the tree is accessible, check that the server is up first.
    """

    _, nfs_server, nfs_path, _, _, _ = urllib.parse.urlparse(tree)
    # Beaker uses a non-standard syntax for NFS URLs, inherited from Cobbler:
    # nfs://server:/path
    # so we need to strip a trailing colon from the hostname portion.
    nfs_server = nfs_server.rstrip(':')
    server_path = os.path.join('/net', nfs_server)
    if nfs_path.startswith('/'):
        nfs_path = nfs_path[1:]
    tree_path = os.path.join(server_path, nfs_path)
    if not os.path.exists(server_path):
        raise NFSServerInaccessible('Cannot access NFS server %s '
                                    'or autofs not running (%s does not exist)'
                                    % (nfs_server, server_path))
    if not os.path.exists(tree_path):
        return False
    return True


def check_url(url):
    """
    Returns True if the given URL exists.
    """

    scheme = urllib.parse.urlparse(url).scheme
    if scheme == 'nfs' or scheme.startswith('nfs+'):
        return check_nfs(url)
    elif scheme == 'http' or scheme == 'https':
        return check_http(url)
    elif scheme == 'ftp':
        return check_ftp(url)
    else:
        raise ValueError('Unrecognised URL scheme %s for tree %s' % (scheme, url))


def check_all_trees(ignore_errors=False,
                    dry_run=False,
                    lab_controller='http://localhost:8000',
                    remove_all=False,
                    filter=None):
    filter_on_arch = True if (filter is not None and filter and 'arch' in filter.keys()) else False
    proxy = xmlrpc_client.ServerProxy(lab_controller, allow_none=True)
    rdistro_trees = []
    distro_trees = proxy.get_distro_trees(filter)
    if not remove_all:
        for distro_tree in distro_trees:
            accessible = False
            for lc, url in distro_tree['available']:
                try:
                    if check_url(url):
                        accessible = True
                    else:
                        print('{0} is missing [Distro Tree ID {1}]'.format(
                            url,
                            distro_tree['distro_tree_id']))
                except (urllib.error.URLError, urllib.error.HTTPError, NFSServerInaccessible) as e:
                    if ignore_errors:
                        # suppress exception, assume the tree still exists
                        accessible = True
                    else:
                        sys.stderr.write('Error checking for existence of URL %s '
                                         'for distro tree %s:\n%s\n'
                                         % (url, distro_tree['distro_tree_id'], e))
                        sys.exit(1)
            if not accessible:
                # All methods were inaccessible!
                rdistro_trees.append(distro_tree)
    else:
        rdistro_trees = distro_trees

    print('INFO: expire_distros to remove %d entries for arch %s' % (len(rdistro_trees),
          filter['arch'] if (filter_on_arch) else 'unset'))

    # If all distro_trees are expired then something is wrong
    # Unless there is intention to remove all distro_trees
    if (len(distro_trees) != len(rdistro_trees)) or remove_all:
        for distro_tree in rdistro_trees:
            if dry_run:
                print('Distro marked for remove %s:%d' % (distro_tree['distro_name'],
                                                          distro_tree['distro_tree_id']))
            else:
                print('Removing distro %s:%d' % (distro_tree['distro_name'],
                                                 distro_tree['distro_tree_id']))
                proxy.remove_distro_trees([distro_tree['distro_tree_id']])
    else:
        if (len(distro_trees) == 0):
            if (filter is None):
                sys.stderr.write('All distros are missing! Please check your server!\n')
                sys.exit(1)
        else:
            sys.stderr.write('Stopped removal of all distros for arch %s!! Please check your '
                             'server.\nYou can manually force removal using --remove-all.\n' %
                             (filter['arch'] if (filter_on_arch) else 'unset'))

def main():
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option('--ignore-errors', default=False, action='store_true',
                      help='Ignore all network errors when communicating with mirrors.')
    parser.add_option('--dry-run', default=False, action='store_true',
                      help='Prints no longer accessible distro without updating the database.')
    parser.add_option('--lab-controller',
                      default='http://localhost:8000',
                      help='Specify which lab controller to import to. '
                           'Defaults to http://localhost:8000.')
    parser.add_option('--remove-all', default=False, action='store_true',
                      help='Remove all distros from lab controller.')
    parser.add_option('--name', default=None,
                      help='Remove all distros with given name. Use "%" for wildcard.')
    parser.add_option('--family', default=None,
                      help='Remove all distros for a given family.')
    parser.add_option('--arch', default=None,
                      help='Remove all distros for a given architecture. When set to "all", '
                           'steps thru each available arch to reduce memory usage.')
    options, args = parser.parse_args()
    startmsg = str("INFO: expire_distros running with --lab-controller=" + options.lab_controller)
    for i in range(1,len(sys.argv)):
        startmsg += ' ' + sys.argv[i]
    print('%s' % (startmsg))
    filter = {}
    if options.name:
        filter['name'] = options.name
    if options.family:
        filter['family'] = options.family

    arch_list = []
    if options.arch:
        if options.arch == "all":
            arch_list = [ "x86_64", "ppc", "ppc64le", "ppc64", "i386", "s390", "s390x", "aarch64", "ia64", "arm", "armhfp" ]
        else:
            arch_list = [ options.arch ]
        for arch in arch_list:
            filter['arch'] = arch
            try:
                check_all_trees(options.ignore_errors,
                                options.dry_run,
                                options.lab_controller,
                                options.remove_all,
                                filter)
            except KeyboardInterrupt:
                pass
    else:
        try:
            check_all_trees(options.ignore_errors,
                            options.dry_run,
                            options.lab_controller,
                            options.remove_all,
                            filter)
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
