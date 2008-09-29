#!/bin/sh

# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material 
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Bill Peck, Gurhan Ozen

arch=$(uname -i)

#Virtualization is only supported on i386, x86_64 or ia64... So we'll seek for 
# hvm data only on those.
if [[ $arch == "i386" || $arch == "x86_64" || $arch == ia64 ]]; then 

   if [ -z $REBOOTCOUNT ]; then
      echo "REBOOTCOUNT variable is not set. Are you in rhts??"
      exit 0;
   fi
 
   if [[ $REBOOTCOUNT == 0 ]]; then
      rhts-run-simple-test $TEST/all_but_hvm ./push-inventory.py
      yum -y install kernel-xen
      if ! rpm -q kernel-xen; then 
         echo "kernel-xen isn't installed. Can't check for HVM capability"
         report_result ${TEST}/hvm FAIL 0
         exit 0
      fi
      if [[ ${arch} == ia64 ]]; then 
         perl -pi.bak -e 's/\tlabel=linux$/\tlabel=linux.old/' /boot/efi/efi/redhat/elilo.conf
         perl -pi.bak2 -e 's/\tlabel=.*?xen$/\tlabel=linux/' /boot/efi/efi/redhat/elilo.conf
      else
         perl -pi.bak -e 's/^default=.*?$/default=0/g' /boot/grub/grub.conf
      fi
      rhts-reboot
   else
      rhts-run-simple-test $TEST/hvm ./push-inventory.py
   fi

else

   rhts-run-simple-test $TEST ./push-inventory.py

fi
    
