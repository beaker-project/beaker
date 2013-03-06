
import sys, os
import xmlrpclib
import urllib2
import urlparse

def url_exists(url):
    try:
        urllib2.urlopen(url, timeout=20)
    except urllib2.URLError:
        return False
    except urllib2.HTTPError:
        return False
    except IOError, e:
        # errno 21 is you tried to retrieve a directory.  Thats ok. We just
        # want to ensure the path is valid so far.
        if e.errno == 21:
            pass
        else:
            raise
    return True

def check_uri(tree):
    """ Make sure the tree is accessible, check that the server is up first.
    """
    url = urlparse.urlparse(tree)
    server_url = '%s://%s' % (url[0], url[1])
    tree_url = '%s%s' % (server_url, url[2])

    if url_exists(server_url) and not url_exists(tree_url):
        return True
    return False

def check_nfs(tree):
    """ Make sure the tree is accessible, check that the server is up first.
    """
    (nfs_server, nfs_path) = tree[6:].split(':', 1)
    server_path = os.path.join('/net', nfs_server)
    if nfs_path.startswith('/'):
        nfs_path = nfs_path[1:]
    tree_path = os.path.join(server_path, nfs_path)
    if os.path.exists(server_path) and not os.path.exists(tree_path):
        return True
    return False

def main():
    proxy = xmlrpclib.ServerProxy('http://localhost:8000', allow_none=True)
    rdistro_trees = []
    distro_trees = proxy.get_distro_trees()
    for distro_tree in distro_trees:
        accessable = False
        for lc, url in distro_tree['available']:
            if url.startswith('nfs://'):
                # Check nfs
                if check_nfs(url):
                    sys.stderr.write("%s is missing\n" % url)
                else:
                    accessable = True
            else:
                # use urllib
                if check_uri(url):
                    sys.stderr.write("%s is missing\n" % url)
                else:
                    accessable = True
        else:
            if not accessable:
                # All methods were unaccessable!
                rdistro_trees.append(distro_tree)

    # if all distro_trees are expired then something is probably wrong.
    if len(distro_trees) != len(rdistro_trees):
        for distro_tree in rdistro_trees:
            print "Removing distro %s:%d" % (distro_tree['distro_name'],
                                             distro_tree['distro_tree_id'])
            proxy.remove_distro_trees([distro_tree['distro_tree_id']])
    else:
        sys.stderr.write("All distros are missing! Please check your server!!\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
