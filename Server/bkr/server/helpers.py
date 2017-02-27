
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from kid import Element, XML
import turbogears
from markdown import markdown
from xml.sax.saxutils import escape as xml_escape
import lxml.etree

def markdown_first_paragraph(text):
    try:
        rendered = markdown(text, safe_mode='escape')
        # Extract the contents of the first <p>
        root = lxml.etree.fromstring('<div>' + rendered + '</div>')
        first_para = root.find('p')
        html_content = ''.join(
                [xml_escape(first_para.text or '')] +
                [lxml.etree.tostring(child) for child in first_para.iterchildren()] +
                [xml_escape(first_para.tail or '')])
        return XML(html_content)
    except Exception:
        return text

def make_link(url, text, elem_class=None, **kwargs):
    # make an <a> element
    a = Element('a', href=turbogears.url(url))
    a.text = text
    if elem_class:
        a.attrib['class'] = elem_class
    a.attrib.update(kwargs)
    return a

def make_edit_link(name, id):
    # make an edit link
    return make_link(url  = 'edit?id=%s' % id,
                     text = name)

def make_remove_link(id):
    # make a remove link
    return XML('<a class="btn" href="remove?id=%s">'
            '<i class="fa fa-times"/> Remove</a>' % id)

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
