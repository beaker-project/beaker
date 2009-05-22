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
# Author: Ales Zelinka <azelinka@redhat.com>

#tries to find test for every existing rl-function
test_coverage(){
	TEST_SCRIPTS=`ls *Test.sh|grep -v coverageTest.sh`
	#doesn't work with redirection, must use temp file instead
	declare -f |grep '^rl.* ()' |grep -v '^rlj'|cut -d ' ' -f 1 >fnc.list
	while read FUNCTION ; do
		assertTrue "function $FUNCTION found in testsuite" "grep -q $FUNCTION $TEST_SCRIPTS"
	done < fnc.list
	rm -f fnc.list
}
