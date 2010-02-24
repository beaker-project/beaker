import sys
import os.path
import beah

def get_root():
    return os.path.abspath(beah.__path__[0])

def main_root():
    print get_root()

def get_data_root():
    rt0 = os.environ.get('BEAH_ROOT', '')
    if rt0 and os.path.isdir(rt0):
        yield os.path.abspath(rt0)
    rt = get_root()
    if not rt:
        ds = ('.', (sys.prefix or "/usr"))
    else:
        ds = ('.', rt, rt + '/..', rt + '/../../../../..', (sys.prefix or "/usr"))
    for d in ds:
        if d:
            d = d + '/share/beah'
            if os.path.isdir(d):
                yield os.path.abspath(d)

def main_data_root():
    print get_data_root().next()

def get_file(fname):
    if os.path.isabs(fname):
        if os.path.isfile(fn):
            return fname
    else:
        for rt in get_data_root():
            fn = rt+'/'+fname
            if os.path.isfile(fn):
                return os.path.abspath(fn)

def main_data_file():
    fn = get_file(sys.argv[1])
    if fn:
        print fn
    else:
        sys.exit(1)

def get_dir(fname):
    if os.path.isabs(fname):
        if os.path.isdir(fn):
            return fname
    else:
        for rt in get_data_root():
            fn = rt+'/'+fname
            if os.path.isdir(fn):
                return os.path.abspath(fn)

def main_data_dir():
    fn = get_dir(sys.argv[1])
    if fn:
        print fn
    else:
        sys.exit(1)

