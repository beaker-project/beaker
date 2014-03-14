
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from kid import Element, XML
import turbogears

def make_link(url, text, **kwargs):
    # make an <a> element
    a = Element('a', href=turbogears.url(url))
    a.text = text
    if kwargs.get('elem_class', None):
        a.attrib['class']=kwargs.get('elem_class')
    return a

def make_edit_link(name, id):
    # make an edit link
    return make_link(url  = 'edit?id=%s' % id,
                     text = name)

def make_remove_link(id):
    # make a remove link
    return XML('<a class="btn" href="remove?id=%s">'
            '<i class="icon-remove"/> Remove</a>' % id)

def make_fake_link(name=None,id=None,text=None,attrs=None):
    # make something look like a href
    a  = Element('a')
    a.attrib['class'] = "link"
    a.attrib['style'] = "color:#22437f;cursor:pointer"
    if name is not None:
        a.attrib['name'] = name
    if id is not None:
        a.attrib['id'] = id
    if text is not None:
        a.text = '%s ' % text
    if attrs is not None:
        for k,v in attrs.items():
            a.attrib[k] = v
    return a
