from kid import Element
import turbogears

def make_link(url, text):
    # make an <a> element
    a = Element('a', {'class': 'list'}, href=turbogears.url(url))
    a.text = text
    return a

def make_edit_link(name, id):
    # make an edit link
    return make_link(url  = 'edit?id=%s' % id,
                     text = name)

def make_remove_link(id):
    # make a remove link
    return make_link(url  = 'remove?id=%s' % id,
                     text = 'Remove (-)')

def make_scan_link(id):
    # make a rescan link
    return make_link(url  = 'rescan?id=%s' % id,
                     text = 'Rescan (*)')

def make_distro_link(distro):
    # make a distro link if distro is defined
    if distro:
        return make_link(url = '/distros/view?id=%s' % distro.id,
                         text = distro.name)
    else:
        return None

def make_system_link(system):
    # make a system link if system is defined
    if system:
        return make_link(url = '/view/%s' % system.fqdn,
                         text = system.fqdn)
    else:
        return None
