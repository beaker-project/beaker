import copy
import os
import kobo.conf

__all__ = ['load_conf', 'get_conf']

_conf = kobo.conf.PyConfigParser()
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
_conf.load_from_file(default_config)
default_system_conf_file = "/etc/beaker/labcontroller.conf"

_conf_loaded = False
def load_conf(conf_file=default_system_conf_file):
    global _conf, _conf_loaded
    # Will throw IOError if file does not exist
    _conf.load_from_file(conf_file)
    _conf_loaded = True

def get_conf():
    global _conf, _conf_loaded
    if not _conf_loaded:
        load_conf()
    return copy.copy(_conf)
