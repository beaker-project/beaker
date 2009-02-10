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
