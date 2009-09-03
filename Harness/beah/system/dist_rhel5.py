from beah.system.dist_rhel import *

def install_rpm(self, pkg_name):
    self.write_line("yum install %s" % pkg_name)

ShExecutable.install_rpm = install_rpm

