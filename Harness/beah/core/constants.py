# Beah - Test harness. Part of Beaker project.
#
# Copyright (C) 2009 Marian Csontos <mcsontos@redhat.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


class RC:
    PASS     = 0
    WARNING  = 50
    FAIL     = 60
    CRITICAL = 70
    FATAL    = 80

    @staticmethod
    def cmp(rc1, rc2):
        """\"Less serious\" RC is less than more serious."""
        return cmp(rc1, rc2)

class LOG_LEVEL:
    DEBUG3   = 10
    DEBUG2   = 20
    DEBUG1   = 30
    INFO     = 40
    WARNING  = 50
    ERROR    = 60
    CRITICAL = 70
    FATAL    = 80
    DEBUG    = DEBUG1

    @staticmethod
    def cmp(level1, level2):
        """\"Less serious\" level is less than more serious."""
        return cmp(level1, level2)

class ECHO:
    OK              = 0
    NOT_IMPLEMENTED = 1
    EXCEPTION       = 2

