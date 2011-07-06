import kobo.conf
import copy, os

_all_ = ['get_conf']

_conf = kobo.conf.PyConfigParser()
default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
_conf.load_from_file(default_config)

main_conf_file = "/etc/beaker/labcontroller.conf"
_conf.load_from_file(main_conf_file)

def get_conf():
    global _conf
    return copy.copy(_conf)
