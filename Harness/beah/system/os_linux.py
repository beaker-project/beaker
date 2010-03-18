from beah import system
import platform, exceptions

class ShExecutable(system.Executable):
    def __init__(self, executable=None, suffix=".sh"):
        system.Executable.__init__(self, executable=executable, suffix=suffix)

    def header(self):
        self.write_line("#!/bin/sh")

    def set_var(self, name, value):
        # FIXME: escape name and value!
        self.write_line("export %s=\"%s\"" % (name, value))

import platform

(DISTNAME,DISTVER,DISTCODENAME) = platform.dist()

def systemdist():
    try:
        sd = __import__('beah.system.dist_'+DISTNAME, {}, {}, ['*'])
    except exceptions.ImportError:
        sd = None
    try:
        sdv = __import__('beah.system.dist_'+DISTNAME+DISTVER, {}, {}, ['*'])
    except exceptions.ImportError:
        sdv = None
    if sdv:
        return sdv
    return sd
