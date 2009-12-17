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

"""
BEAker Harness. Part of Beaker project [http://fedorahosted.org/beaker/wiki].
"""

__import__('pkg_resources').declare_namespace(__name__)

# FIXME:
# see beaker/Client/src/beaker/__init__.py:
#-------------------------------------------------------------------------------
# See http://peak.telecommunity.com/DevCenter/setuptools#namespace-packages
#try:
#    __import__('pkg_resources').declare_namespace(__name__)
#except ImportError:
#    from pkgutil import extend_path
#    __path__ = extend_path(__path__, __name__)
#-------------------------------------------------------------------------------
# Q: Why?
