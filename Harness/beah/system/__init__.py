import os, tempfile, exceptions, stat, platform
import sys

# FIXME: There should be an OS independent way to create
# executables!
# - setting variable
# - running executable
# - downloading a file (wget)
# - installing an rpm (rpm)
# - yum/up2date (linux only)


class Executable(object):
    def __init__(self, executable=None, suffix="None"):
        self.line_end = "\n"
        self.fd = None
        self.executable = executable
        self.suffix = suffix

    def create(self):
        if self.executable:
            self.fd = os.open(self.executable, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        else:
            (self.fd, self.executable) = tempfile.mkstemp(suffix=self.suffix)

    def write_line(self, line):
        self.__content += line+self.line_end

    def make_content(self):
        self.__content = ""
        self.header()
        self.content()
        self.footer()
        return self.__content

    def make(self):
        self.create()
        os.write(self.fd, self.make_content())
        self.close()

    def close(self):
        os.close(self.fd)
        self.fd = None
        os.chmod(self.executable, stat.S_IREAD | stat.S_IEXEC)

    def header(self):
        pass

    def content(self):
        raise exceptions.NotImplementedError

    def footer(self):
        pass


class PyExecutable(Executable):
    def __init__(self, executable=None, suffix=".py"):
        Executable.__init__(self, executable=executable, suffix=suffix)

    def header(self, fd):
        self.write_line("#!"+sys.executable)


ARCH = platform.machine()
def systemarch():
    try:
        return __import__('beah.system.arch_'+ARCH, {}, {}, ['*'])
    except exceptions.ImportError:
        return None

OS = platform.system().lower()
def systemos():
    try:
        return __import__('beah.system.os_'+OS, {}, {}, ['*'])
    except exceptions.ImportError:
        return None

