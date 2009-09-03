from beah.system.dist_fedora import *

# FIXME:
def install_rpm(self, pkg_name):
    self.write_line("up2date --install %s" % pkg_name)

ShExecutable.install_rpm = install_rpm

