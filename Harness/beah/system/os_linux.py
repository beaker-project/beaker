from beah import system
import platform, exceptions

class ShExecutable(system.Executable):
    def __init__(self, executable=None, suffix=".sh"):
        system.Executable.__init__(self, executable=executable, suffix=suffix)

    def header(self):
        self.write_line("#!/bin/sh")

    def set_var(self, name, value):
        # FIXME: escape name and value!
        self.write_line("export %s=%s" % (name, value))

import platform

(DISTNAME,DISTVER,DISTCODENAME) = platform.dist()

systemdist = None
try:
    systemdist = __import__('beah.system.dist_'+DISTNAME, fromlist=['*'])
except exceptions.ImportError:
    pass

try:
    systemdist = __import__('beah.system.dist_'+DISTNAME+DISTVER, fromlist=['*'])
except exceptions.ImportError:
    pass

