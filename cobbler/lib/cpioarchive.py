""" cpioarchive: Support for cpio archives
Copyright (C) 2006 Ignacio Vazquez-Abrams """

""" This library is free software; you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation; either version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA """

import atexit

def version():
  """Returns the version number of the module."""
  return '0.1'

class CpioError(Exception):
  """Exception class for cpioarchive exceptions"""
  pass

class CpioEntry(object):
  """Information about a single file in a cpio archive. Provides a file-like
interface for interacting with the entry."""
  def __init__(self, hdr, cpio, offset):
    """Create a new CpioEntry instance. Internal use only."""
    if len(hdr)<110:
      raise CpioError('cpio header too short')
    if not hdr.startswith('070701'):
      raise CpioError('cpio header invalid')
    self.inode=int(hdr[6:14], 16)
    self.mode=int(hdr[14:22], 16)
    self.uid=int(hdr[22:30], 16)
    self.gid=int(hdr[30:38], 16)
    self.nlinks=int(hdr[38:46], 16)
    self.mtime=int(hdr[46:54], 16)
    self.size=int(hdr[54:62], 16)
    """Size of the file stored in the entry."""
    self.devmajor=int(hdr[62:70], 16)
    self.devminor=int(hdr[70:78], 16)
    self.rdevmajor=int(hdr[78:86], 16)
    self.rdevminor=int(hdr[86:94], 16)
    namesize=int(hdr[94:102], 16)
    self.checksum=int(hdr[102:110], 16)
    if len(hdr)<110+namesize:
      raise CpioError('cpio header too short')
    self.name=hdr[110:110+namesize-1]
    """Name of the file stored in the entry."""
    self.datastart=offset+110+namesize
    self.datastart+=(4-(self.datastart%4))%4
    self.curoffset=0
    self.cpio=cpio
    self.closed=False

  def close(self):
    """Close this cpio entry. Further calls to methods will raise an
exception."""
    self.closed=True
    
  def flush(self):
    """Flush the entry (no-op)."""
    pass

  def read(self, size=None):
    """Read data from the entry.

Keyword arguments:
size -- Number of bytes to read (default: whole entry)
"""
    if self.closed:
      raise ValueError('read operation on closed file')
    self.cpio.file.seek(self.datastart+self.curoffset, 0)
    if size and size<self.size-self.curoffset:
      ret=self.cpio.file.read(size)
    else:
      ret=self.cpio.file.read(self.size-self.curoffset)
    self.curoffset+=len(ret)
    return ret

  def seek(self, offset, whence=0):
    """Move to new position within an entry.
    
Keyword arguments:
offset -- Byte count
whence -- Describes how offset is used.
  0: From beginning of file
  1: Forwards from current position
  2: Backwards from current position
  Other values are ignored.
"""
    if self.closed:
      raise ValueError('seek operation on closed file')
    if whence==0:
      self.curoffset=offset
    elif whence==1:
      self.curoffset+=offset
    elif whence==2:
      self.curoffset-=offset
    self.curoffset=min(max(0, self.curoffset), self.size)

  def tell(self):
    """Get current position within an entry"""
    if self.closed:
      raise ValueError('tell operation on closed file')
    return self.curoffset

class CpioArchive(object):
  @classmethod
  def open(name=None, mode='r', fileobj=None):
    """Open a cpio archive. Defers to CpioArchive.__init__()."""
    return CpioArchive(name, mode, fileobj)
  
  def __init__(self, name=None, mode='r', fileobj=None):
    """Open a cpio archive.

Keyword arguments:
name -- Filename to open (default: open a file object instead)
mode -- Filemode to open the archive in (default: read-only)
fileobj -- File object to use (default: open by filename instead)
"""
    if not mode=='r':
      raise NotImplementedError()
    self._infos=[]
    if name:
      self._readfile(name)
      self.external=False
    elif fileobj:
      self._readobj(fileobj)
      self.external=True
    else:
      raise CpioError('Oh come on! Pass me something to work with...')
    self._ptr=0
    self.closed=False
    atexit.register(self.close)

  def close(self):
    """Close the CpioArchive. Also closes all associated entries."""
    if self.closed:
      return
    [x.close() for x in self._infos]
    self.closed=True
    if not self.external:
      self.file.close()

  def next(self):
    """Return the next entry in the archive."""
    if self.closed:
      raise ValueError('next operation on closed file')
    if self._ptr>len(self._infos):
      raise StopIteration()
    ret=self._infos[self._ptr]
    self._ptr+=1
    return ret

  def __iter__(self):
    return iter(self._infos)

  def _readfile(self, name):
    self._readobj(file(name, 'rb'))
    
  def _readobj(self, fileobj):
    self.file=fileobj
    start=self.file.tell()
    istart=self.file.tell()
    text=self.file.read(110)
    while text:
      namelen=int(text[94:102], 16)
      text+=self.file.read(namelen)
      ce=CpioEntry(text, self, istart)
      if not ce.name=="TRAILER!!!":
        self._infos.append(ce)
      else:
	return
      self.file.seek((4-(self.file.tell()-istart)%4)%4, 1)
      self.file.seek(self._infos[-1].size, 1)
      self.file.seek((4-(self.file.tell()-istart)%4)%4, 1)

      istart=self.file.tell()
      text=self.file.read(110)
    else:
      raise CpioError('premature end of headers')
