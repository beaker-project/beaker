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

def make_progress_bar(item):
    pwidth=0
    wwidth=0
    fwidth=0
    kwidth=0
    completed=0
    if not getattr(item, 'ttests', None):
        return None
    if getattr(item, 'ptests', None):
        completed += item.ptests
        pwidth = int(float(item.ptests)/float(item.ttests)*100)
    if getattr(item, 'wtests', None):
        completed += item.wtests
        wwidth = int(float(item.wtests)/float(item.ttests)*100)
    if getattr(item, 'ftests', None):
        completed += item.ftests
        fwidth = int(float(item.ftests)/float(item.ttests)*100)
    if getattr(item, 'ktests', None):
        completed += item.ktests
        kwidth = int(float(item.ktests)/float(item.ttests)*100)
    percentCompleted = int(float(completed)/float(item.ttests)*100)
    div   = Element('div', {'class': 'dd'})
    div.append(Element('div', {'class': 'green', 'style': 'width:%s%%' % pwidth}))
    div.append(Element('div', {'class': 'orange', 'style': 'width:%s%%' % wwidth}))
    div.append(Element('div', {'class': 'red', 'style': 'width:%s%%' % fwidth}))
    div.append(Element('div', {'class': 'blue', 'style': 'width:%s%%' % kwidth}))
    div.tail = "%s%%" % percentCompleted
    return div
