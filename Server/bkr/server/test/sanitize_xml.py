#!/usr/bin/python
#Simple helper to remove confidential data from xml results

import sys
import xml.dom.minidom

tasks = {}
count = 0
doc = xml.dom.minidom.Document()
oldjob = xml.dom.minidom.parseString(open(sys.argv[1]).read()).getElementsByTagName('job')[0]
newjob = doc.createElement('job')

def handle_recipe(element, node):
    global count
    new_r = doc.createElement(element)
    new_r.setAttribute('result', node.getAttribute('result'))
    new_r.setAttribute('status', node.getAttribute('status'))
    new_r.setAttribute('whiteboard', '')
    new_dr = doc.createElement('distroRequires')
    new_dn = doc.createElement('distro_name')
    new_dn.setAttribute('op','=')
    new_dn.setAttribute('value','BlueShoeLinux5-5')
    new_dr.appendChild(new_dn)
    new_r.appendChild(new_dr)
    new_r.appendChild(doc.createElement('hostRequires'))
    for child in node.childNodes:
        if child.nodeName == 'guestrecipe':
            new_r.appendChild(handle_recipe('guestrecipe', child))
        if child.nodeName == 'task':
            new_t = doc.createElement('task')
            if child.getAttribute('name') not in tasks:
                tasks[child.getAttribute('name')] = '/fake/Task/task%s' % count
                count += 1
            new_t.setAttribute('name', tasks[child.getAttribute('name')])
            new_t.setAttribute('result', child.getAttribute('result'))
            new_t.setAttribute('status', child.getAttribute('status'))
            new_r.appendChild(new_t)
    return new_r
    
newjob.setAttribute('result', oldjob.getAttribute('result'))
newjob.setAttribute('status', oldjob.getAttribute('status'))
newjob.appendChild(doc.createElement('whiteboard'))
for old_rs in oldjob.getElementsByTagName('recipeSet'):
    new_rs = doc.createElement('recipeSet')
    for child in old_rs.childNodes:
        if child.nodeName == 'recipe':
            new_r = handle_recipe('recipe', child)
            new_rs.appendChild(new_r)
    newjob.appendChild(new_rs)
print newjob.toprettyxml()
