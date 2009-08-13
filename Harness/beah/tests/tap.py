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

################################################################################
# TEST STRINGS:
################################################################################
tests = [
"""\
""",

"""\

""",

"""\
This line is a syntactic error
""",

"""\
1..0
""",

"""\
1..0 # TODO add some tests here
""",

"""\
1..0 # SKIP the whole plan
# a comment
# SKIP comment
# TODO comment
ok 1 test out of plan # SKIP this test
not ok 2 second test out of plan
not ok third test out of plan # TODO expected failure
ok fourth test out of plan
""",

"""\
1..1
# a comment
ok first test
# more comments
""",

"""\
1..1
not ok first test
# diagnostics: missing file
""",

"""\
1..1
ok 1 ;-)
ok 2 :-(
ok :-(
""",

"""\
1..2
not ok 2 :-)
ok 1 :-)
ok :-/
not ok 2 :-O
not ok :-(
""",

"""\
not ok
ok
ok
ok
not ok
""",
]

__CAT_STR_SH="""\
#!/bin/bash
cat - <<END
%s
END
"""

__DELAY_CAT_STR_SH="""\
#!/bin/bash
function delay_cat()
{
    while read line; do
        sleep ${1:-1}
        echo "$line"
    done
}
delay_cat %d <<END
%s
END
"""

__TS_CAT_STR_SH="""\
#!/bin/bash
function ts_cat()
{
    while read line; do
        echo "$(date "${1:-"+%Y%m%d-%H%M%S.%N"}"): $line"
    done
}
delay_cat %s <<END
%s
END
"""

__RUN_TAP_TASK="""\
#!/usr/bin/env python
import sys
sys.path.append(%s)
# FIXME: there is not task module!
import task
t = task.Perl_Test_Harness_TAP_Task(%s)
t.run()
"""

################################################################################
# TESTING TASKS:
################################################################################
import tempfile, os
def mkexecutable(str):
    (file, filename) = tempfile.mkstemp()
    os.write(file, str)
    os.close(file)
    os.chmod(filename, 0700)
    return filename

import sys
def run_on_backend(backend):
    for test in tests:
        test_filename = mkexecutable(__CAT_STR_SH % test)
        try:
            print "Backend: Test written to file %s" % test_filename
            task_filename = mkexecutable(__RUN_TAP_TASK % (repr(sys.path[0]), repr(test_filename)))
            try:
                print "Backend: Task written to file %s" % task_filename
                print "Backend: Sending task %s to server" % task_filename
                # FIXME: backend's API changed!
                backend.send_run(task_filename)
                print "Backend: Data written"
                yield task_filename
                print "Backend: Task %s completed" % task_filename
            finally:
                os.unlink(task_filename)
        finally:
            os.unlink(test_filename)

# FIXME: there is not task module!
#import task
#def run_as_tasks():
#    for test in tests:
#        test_filename = mkexecutable(__CAT_STR_SH % test)
#        t = task.Perl_Test_Harness_TAP_Task(test_filename)
#        t.run()
#        os.unlink(test_filename)
#
#if __name__ == '__main__':
#    run_as_tasks()
