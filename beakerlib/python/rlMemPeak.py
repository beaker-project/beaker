#!/usr/bin/env python

# Authors:  Petr Muller     <pmuller@redhat.com> 
#
# Description: Prints a memory consumption peak of an executed program
#
# Copyright (c) 2008 Red Hat, Inc. All rights reserved. This copyrighted
# material is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import sys, time, re

use_sub   = False
use_popen = False

try:
  import subprocess
  use_sub = True
except ImportError:
  import popen2
  use_popen = True

if len(sys.argv) < 2:
  print 'syntax: rlMemPeak <command>'
  sys.exit(1)

proglist = sys.argv[1:]

if use_sub:
  task = subprocess.Popen(proglist)
elif use_popen:
  task = popen2.Popen3(" ".join(proglist))

maxmem = 0
fn = '/proc/%d/status' % task.pid
mre = re.compile(r'VmRSS:[ \t]+(?P<mem>\d+)')

while True:
  for line in open(fn, 'r').readlines():
    m = mre.search(line)
    if m:
      mem = int(m.group('mem'))
      maxmem = max(mem, maxmem)
      break
  time.sleep(0.1)
  finish = task.poll()
  if (use_sub and finish != None) or (use_popen and finish != -1):
    break

print "%d" % (maxmem)
