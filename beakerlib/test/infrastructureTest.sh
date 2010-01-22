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
# Author: Petr Splichal <psplicha@redhat.com>

#
# rlFileBackup & rlFileRestore unit test
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# this test has to be run as root
# [to restore ownership, permissions and attributes]
# run with DEBUG=1 to get more details about progress

BackupSanityTest() {
    # detect selinux & acl support
    [ -d "/selinux" ] && local selinux=true || local selinux=false
    setfacl -m u:root:rwx $BEAKERLIB_DIR &>/dev/null \
            && local acl=true || local acl=false
    [ -d "$BEAKERLIB_DIR" ] && chmod -R 777 "$BEAKERLIB_DIR" \
            && rm -rf "$BEAKERLIB_DIR" && rlJournalStart
    score=0

    list() {
        ls -ld --full-time directory
        ls -lL --full-time directory
        $acl && getfacl -R directory
        $selinux && ls -Z directory
        cat directory/content
    }

    mess() {
        echo -e "\nBackupSanityTest: $1"
    }

    fail() {
        echo "BackupSanityTest FAIL: $1"
        ((score++))
    }

    # setup
    tmpdir=`mktemp -d /tmp/backup-test-XXXXXXX`
    pushd $tmpdir >/dev/null

    # create files
    mkdir directory
    pushd directory >/dev/null
    mkdir -p sub/sub/dir
    mkdir 'dir with spaces'
    mkdir 'another dir with spaces'
    touch file permissions ownership times context acl
    echo "hello" >content
    ln file hardlink
    ln -s file softlink
    chmod 750 permissions
    chown nobody.nobody ownership
    touch --reference /var/www times
    $acl && setfacl -m u:root:rwx acl
    $selinux && chcon --reference /var/www context
    popd >/dev/null

    # save details and backup
    list >original
    mess "Doing the backup"
    rlFileBackup directory || fail "Backup"

    # remove completely
    mess "Testing restore after complete removal "
    rm -rf directory
    rlFileRestore || fail "Restore after complete removal"
    list >removal
    diff original removal || fail "Restore after complete removal not ok, differences found"

    # remove some, change content
    mess "Testing restore after partial removal"
    rm -rf directory/sub/sub directory/hardlink directory/permissions 'dir with spaces'
    echo "hi" >directory/content
    rlFileRestore || fail "Restore after partial removal"
    list >partial
    diff original partial || fail "Restore after partial removal not ok, differences found"

    # attribute changes
    mess "Testing restore after attribute changes"
    pushd directory >/dev/null
    chown root ownership
    chown nobody file
    touch times
    chmod 777 permissions
    $acl && setfacl -m u:root:---
    $selinux && chcon --reference /home context
    popd >/dev/null
    rlFileRestore || fail "Restore attributes"
    list >attributes
    diff original attributes || fail "Restore attributes not ok, differences found"

    # acl check for correct path restore
    if $acl; then
        mess "Checking that path ACL is correctly restored"
        # create acldir with modified ACL
        pushd directory >/dev/null
        mkdir acldir
        touch acldir/content
        setfacl -m u:root:--- acldir
        popd >/dev/null
        list >original
        # backup it's contents (not acldir itself)
        rlFileBackup directory/acldir/content
        rm -rf directory/acldir
        # restore & check for differences
        rlFileRestore || fail "Restore path ACL"
        list >acl
        diff original acl || fail "Restoring correct path ACL not ok"
    fi

    # clean up
    popd >/dev/null
    rm -rf $tmpdir

    mess "Total score: $score"
    return $score
}


test_rlFileBackupAndRestore() {
    assertFalse "rlFileRestore should fail when no backup was done" \
        'rlFileRestore'
    assertTrue "rlFileBackup should fail and return 2 when no file/dir given" \
        'rlFileBackup; [ $? == 2 ]'
    assertFalse "rlFileBackup should fail when given file/dir does not exist" \
        'rlFileBackup i-do-not-exist'

    if [ "$DEBUG" == "1" ]; then
        BackupSanityTest
    else
        BackupSanityTest >/dev/null 2>&1
    fi
    assertTrue "rlFileBackup & rlFileRestore sanity test (needs to be root to run this)" $?
    chmod -R 777 "$BEAKERLIB_DIR/backup" && rm -rf "$BEAKERLIB_DIR/backup"
}

test_rlFileBackupCleanAndRestore() {
    test_dir=$(mktemp -d /tmp/beakerlib-test-XXXXXX)
    date > "$test_dir/date1"
    date > "$test_dir/date2"
    if [ "$DEBUG" == "1" ]; then
        rlFileBackup --clean "$test_dir"
    else
        rlFileBackup --clean "$test_dir" >/dev/null 2>&1
    fi
    rm -f "$test_dir/date1"   # should be restored
    date > "$test_dir/date3"   # should be removed
    ###tree "$test_dir"
    if [ "$DEBUG" == "1" ]; then
        rlFileRestore
    else
        rlFileRestore >/dev/null 2>&1
    fi
    ###tree "$test_dir"
    assertTrue "rlFileBackup with '--clean' option adds" \
        "ls '$test_dir/date1'"
    assertFalse "rlFileBackup with '--clean' option removes" \
        "ls '$test_dir/date3'"
    chmod -R 777 "$BEAKERLIB_DIR/backup" && rm -rf "$BEAKERLIB_DIR/backup"
}

test_rlFileBackupCleanAndRestoreWhitespace() {
    test_dir=$(mktemp -d '/tmp/beakerlib-test-XXXXXX')
    mkdir "$test_dir/noclean"
    mkdir "$test_dir/noclean clean"
    mkdir "$test_dir/aaa"
    date > "$test_dir/noclean/date1"
    date > "$test_dir/noclean clean/date2"
    if [ "$DEBUG" == "1" ]; then
        rlFileBackup "$test_dir/noclean"
        rlFileBackup --clean "$test_dir/noclean clean"
        rlFileBackup --clean "$test_dir/aaa"
    else
        rlFileBackup "$test_dir/noclean" >/dev/null 2>&1
        rlFileBackup --clean "$test_dir/noclean clean" >/dev/null 2>&1
    fi
    ###tree "$test_dir"
    date > "$test_dir/noclean/date3"   # this should remain
    date > "$test_dir/noclean clean/date4"   # this should be removed
    ###tree "$test_dir"
    if [ "$DEBUG" == "1" ]; then
        rlFileRestore
    else
        rlFileRestore >/dev/null 2>&1
    fi
    ###tree "$test_dir"
    assertTrue "rlFileBackup without '--clean' do not remove in dir with spaces" \
        "ls '$test_dir/noclean/date3'"
    assertFalse "rlFileBackup with '--clean' remove in dir with spaces" \
        "ls '$test_dir/noclean clean/date4'"
    chmod -R 777 "$BEAKERLIB_DIR/backup" && rm -rf "$BEAKERLIB_DIR/backup"
}



test_rlServiceStart() {
    assertTrue "rlServiceStart should fail and return 99 when no service given" \
        'rlServiceStart; [ $? == 99 ]'
    assertTrue "rlServiceStop should fail and return 99 when no service given" \
        'rlServiceStart; [ $? == 99 ]'
    assertTrue "rlServiceRestore should fail and return 99 when no service given" \
        'rlServiceStart; [ $? == 99 ]'

    assertTrue "down-starting-pass" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlRun "rlServiceStart down-starting-pass"'

    assertTrue "down-starting-ok" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceStart down-starting-ok'

    assertTrue "up-starting-ok" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceStart up-starting-ok'

    assertTrue "weird-starting-ok" \
        'service() { case $2 in status) return 33;; start) return 0;; stop) return 0;; esac; };
        rlServiceStart weird-starting-ok'

    assertFalse "up-starting-stop-ko" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 1;; esac; };
        rlServiceStart up-starting-stop-ko'

    assertFalse "up-starting-stop-ok-start-ko" \
        'service() { case $2 in status) return 0;; start) return 1;; stop) return 0;; esac; };
        rlServiceStart up-starting-stop-ok-start-ko'

    assertFalse "down-starting-start-ko" \
        'service() { case $2 in status) return 3;; start) return 1;; stop) return 0;; esac; };
        rlServiceStart down-starting-start-ko'

    assertFalse "weird-starting-start-ko" \
        'service() { case $2 in status) return 33;; start) return 1;; stop) return 0;; esac; };
        rlServiceStart weird-starting-start-ko'
}

test_rlServiceStop() {
    assertTrue "down-stopping-ok" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceStop down-stopping-ok'

    assertTrue "up-stopping-ok" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceStop up-stopping-ok'

    assertTrue "weird-stopping-ok" \
        'service() { case $2 in status) return 33;; start) return 0;; stop) return 0;; esac; };
        rlServiceStop weird-stopping-ok'

    assertFalse "up-stopping-stop-ko" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 1;; esac; };
        rlServiceStop up-stopping-stop-ko'
}

test_rlServiceRestore() {
    assertTrue "was-down-is-down-ok" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceStop was-down-is-down-ok;
        service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceRestore was-down-is-down-ok'

    assertTrue "was-down-is-up-ok" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceStart was-down-is-up-ok;
        service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceRestore was-down-is-up-ok'

    assertTrue "was-up-is-down-ok" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceStop was-up-is-down-ok;
        service() { case $2 in status) return 3;; start) return 0;; stop) return 0;; esac; };
        rlServiceRestore was-up-is-down-ok'

    assertTrue "was-up-is-up-ok" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceStart was-up-is-up-ok;
        service() { case $2 in status) return 0;; start) return 0;; stop) return 0;; esac; };
        rlServiceRestore was-up-is-up-ok'

    assertFalse "was-up-is-up-stop-ko" \
        'service() { case $2 in status) return 0;; start) return 0;; stop) return 1;; esac; };
        rlServiceStart was-up-is-up-stop-ko;
        service() { case $2 in status) return 0;; start) return 0;; stop) return 1;; esac; };
        rlServiceRestore was-up-is-up-stop-ko'

    assertFalse "was-down-is-up-stop-ko" \
        'service() { case $2 in status) return 3;; start) return 0;; stop) return 1;; esac; };
        rlServiceStart was-down-is-up-stop-ko;
        service() { case $2 in status) return 0;; start) return 0;; stop) return 1;; esac; };
        rlServiceRestore was-down-is-up-stop-ko'

    assertFalse "was-up-is-down-start-ko" \
        'service() { case $2 in status) return 0;; start) return 1;; stop) return 0;; esac; };
        rlServiceStop was-up-is-down-start-ko;
        service() { case $2 in status) return 3;; start) return 1;; stop) return 0;; esac; };
        rlServiceRestore was-up-is-down-start-ko'

    assertFalse "was-up-is-up-start-ko" \
        'service() { case $2 in status) return 0;; start) return 1;; stop) return 0;; esac; };
        rlServiceStart was-up-is-up-start-ko;
        service() { case $2 in status) return 0;; start) return 1;; stop) return 0;; esac; };
        rlServiceRestore was-up-is-up-start-ko'
}


#FIXME: no idea how to really test these mount function
MP="beakerlib-test-mount-point"
[ -d "$MP" ] && rmdir "$MP"

test_rlMount(){
    mkdir "$MP"
    mount() { return 0 ; }
    assertTrue "rlMount returns 0 when internal mount succeeds" \
    "mount() { return 0 ; } ; rlMount server remote_dir $MP"
    assertFalse "rlMount returns 1 when internal mount doesn't succeeds" \
    "mount() { return 4 ; } ; rlMount server remote_dir $MP"
    rmdir "$MP"
}

test_rlMountAny(){
    assertTrue "rlmountAny is marked as deprecated" \
    "rlMountAny server remotedir $MP |grep -q deprecated "
}

test_rlAnyMounted(){
    assertTrue "rlAnymounted is marked as deprecated" \
    "rlAnyMounted server remotedir $MP |grep -q deprecated "
}

test_rlCheckMount(){
    [ -d "$MP" ] && rmdir "$MP"
    assertFalse "rlCheckMount returns non-0 on no-existing mount point" \
    "rlCheckMount server remotedir $MP"
}
test_rlAssertMount(){
    mkdir "$MP"
    __one_fail_one_pass "rlAssertMount server remote-dir $MP" "FAIL"
    assertFalse "rlAssertMount without paramaters doesn't succeed" \
    "rlAssertMount"
}


