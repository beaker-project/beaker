import copy
import os
import kobo.conf

__all__ = ['get_conf']

_conf = kobo.conf.PyConfigParser()
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
_conf.load_from_file(default_config)
default_system_conf_file = "/etc/beaker/labcontroller.conf"
conf_file = os.environ.get('BEAKER_LABCONTROLLER_CONFIG_FILE') or default_system_conf_file

# Will throw IOError if file does not exist
_conf.load_from_file(conf_file)

def get_conf():
    global _conf
    return copy.copy(_conf)
