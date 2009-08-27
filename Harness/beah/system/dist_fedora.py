from beah.system import os_linux

def install_rpm(self, pkg_name):
    self.write_line("yum install %s" % pkg_name)

os_linux.ShExecutable.install_rpm = install_rpm

class RPMInstaller(os_linux.ShExecutable):
    def __init__(self, rpm):
        self.rpm = rpm
        os_linux.ShExecutable.__init__(self)

    def content(self):
        self.install_rpm(self.rpm)

