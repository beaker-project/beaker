from kid import Element
import turbogears, sys
from turbogears.database import session

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

def make_fake_link(name,id,text):
    # make something look like a href
    a  = Element('a')
    a.attrib['class'] = "list"
    a.attrib['style'] = "color:#22437f;cursor:pointer"
    a.attrib['name'] = name
    a.attrib['id'] = id
    a.text = '%s ' % text
    return a

def _sanitize_list(list):
    for item in list:
        _sanitize_amqp(item)

def _sanitize_dict(dict):
    for k,v in dict.iteritems():
        _sanitize_amqp(k)
        _sanitize_amqp(v)

def _sanitize_amqp(data):
    """
    Ensures that data are valid types to be sent over AMQP
    """
    from bkr.common.message_bus import VALID_AMQP_TYPES
    types = {list: _sanitize_list,
             dict: _sanitize_dict,
             }
    data_type = type(data)
    if data_type not in VALID_AMQP_TYPES:
        raise ValueError('%s is not a valid type to send over AMQP. Not sending' % data_type)
    try: #Raises KeyError if we arent a list or dict, that's fine
        types[type(data)](data)
    except KeyError:
        pass

def sanitize_amqp(f):
    """
    this decorator will check that methods are exposed
    and have suitable data for AMQP
    """
    def sanity(*args, **kw):
        output = f(*args,**kw)
        _sanitize_amqp(output)
        return output
    return sanity
