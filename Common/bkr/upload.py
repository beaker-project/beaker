import base64
import os
import stat
import errno
import fcntl
import logging

try:
    from hashlib import md5 as md5_constructor
except ImportError:
    from md5 import new as md5_constructor

logger = logging.getLogger(__name__)

def decode_int(n):
    """If n is not an integer, attempt to convert it"""
    if isinstance(n, (int, long)):
        return n
    return int(n)

def ensuredir(directory):
    """Create directory, if necessary."""
    if os.path.isdir(directory):
        return
    try:
        os.makedirs(directory)
    except OSError:
        #thrown when dir already exists (could happen in a race)
        if not os.path.isdir(directory):
            #something else must have gone wrong
            raise

class Uploader:
    def __init__(self, basepath):
        self.basepath = basepath

    def uploadFile(self, path, name, size, md5sum, offset, data):
        #path: the relative path to upload to
        #name: the name of the file
        #size: size of contents (bytes)
        #md5: md5sum (hex digest) of contents
        #data: base64 encoded file contents
        #offset: the offset of the chunk
        # files can be uploaded in chunks, if so the md5 and size describe
        # the chunk rather than the whole file. the offset indicates where
        # the chunk belongs
        # the special offset -1 is used to indicate the final chunk
        contents = base64.decodestring(data)
        del data
        # we will accept offset and size as strings to work around xmlrpc limits
        offset = decode_int(offset)
        size = decode_int(size)
        if offset != -1:
            if size is not None:
                if size != len(contents): return False
            if md5sum:
                if md5sum != md5_constructor(contents).hexdigest():
                    return False
        uploadpath = self.basepath
        #XXX - have an incoming dir and move after upload complete
        # SECURITY - ensure path remains under uploadpath
        path = os.path.normpath(path)
        if path.startswith('..'):
            logger.warn('Upload path not allowed: %s' % path)
            raise BX(_("Upload path not allowed: %s" % path))
        udir = "%s/%s" % (uploadpath,path)
        ensuredir(udir)
        fn = "%s/%s" % (udir,name)
        try:
            st = os.lstat(fn)
        except OSError, e:
            # Only offset 0 should be allowed to create a file.
            if e.errno == errno.ENOENT and offset == 0:
                pass
            else:
                logger.warn('ENOENT and offset != 0 for %s' % fn)
                raise
        else:
            if not stat.S_ISREG(st.st_mode):
                logger.warn('destination not a file: %s' % fn)
                raise BX(_("destination not a file: %s" % fn))
        fd = os.open(fn, os.O_RDWR | os.O_CREAT, 0666)
        # log_error("fd=%r" %fd)
        try:
            if offset == 0 or (offset == -1 and size == len(contents)):
                #truncate file
                fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                try:
                    os.ftruncate(fd, 0)
                    # log_error("truncating fd %r to 0" %fd)
                finally:
                    fcntl.lockf(fd, fcntl.LOCK_UN)
            if offset == -1:
                os.lseek(fd,0,2)
            else:
                os.lseek(fd,offset,0)
            #write contents
            fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB, len(contents), 0, 2)
            try:
                os.write(fd, contents)
                # log_error("wrote contents")
            finally:
                fcntl.lockf(fd, fcntl.LOCK_UN, len(contents), 0, 2)
            if offset == -1:
                if size is not None:
                    #truncate file
                    fcntl.lockf(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
                    try:
                        os.ftruncate(fd, size)
                        # log_error("truncating fd %r to size %r" % (fd,size))
                    finally:
                        fcntl.lockf(fd, fcntl.LOCK_UN)
                if md5sum:
                    #check final md5sum
                    sum = md5_constructor()
                    fcntl.lockf(fd, fcntl.LOCK_SH|fcntl.LOCK_NB)
                    try:
                        # log_error("checking md5sum")
                        os.lseek(fd,0,0)
                        while True:
                            block = os.read(fd, 819200)
                            if not block: break
                            sum.update(block)
                        if md5sum != sum.hexdigest():
                            # log_error("md5sum did not match")
                            #os.close(fd)
                            logger.warn('md5sum did not match for %s' % fn)
                            return False
                    finally:
                        fcntl.lockf(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)
        return True

