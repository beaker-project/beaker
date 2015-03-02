#!/bin/bash

# On Fedora, this script installs the necessary packages and sets up the database
# to run Beaker's test suite.

# You should run this as root from the Misc/ directory of a git clone
# of the source repository

# Abort if any of these fails
set -e

# add the beaker-server-testing repo
pushd /etc/yum.repos.d/
cat >/etc/yum.repos.d/beaker-server-testing.repo <<"EOF"
[beaker-server-testing]
name=Beaker Server -Fedora$releasever - Testing
baseurl=http://beaker-project.org/yum/server-testing/Fedora$releasever/
enabled=1
gpgcheck=0

EOF

popd

# create beaker RPMs

pushd ../

yum-builddep -y beaker.spec
yum -y install createrepo rpm-build
Misc/rpmbuild.sh -bb
mv rpmbuild-output /tmp/beaker-rpms
createrepo --no-database /tmp/beaker-rpms

cat >/etc/yum.repos.d/beaker-local-builds.repo <<"EOF"
[beaker-builds]
name=beaker-builds
baseurl=file:///tmp/beaker-rpms
EOF

popd

# Find the dependencies
yum deplist beaker-server beaker-lab-controller beaker-integration-tests beaker-client beaker | grep 'provider' | grep -v 'beaker*' | awk '{print $2'} | sort -u > beaker_deplist

# others
echo "git" >> beaker_deplist
echo "mariadb-server" >> beaker_deplist
echo "mariadb" >> beaker_deplist
echo "openldap-servers" >> beaker_deplist

# Install them
while read line
do
    yum -y install `yum info $line | grep 'Name' | awk '{print $3}'`
done <beaker_deplist


#setup mariadb
cp /etc/my.cnf /etc/my.cnf-orig
cat /etc/my.cnf-orig | awk '
        {print $0};
        /\[mysqld\]/ {
            print "character-set-server=utf8";
        }' > /etc/my.cnf
systemctl restart mysqld
echo "CREATE DATABASE beaker_test;" | mysql
echo "GRANT ALL ON beaker_test.* TO 'beaker'@'localhost' IDENTIFIED BY
'beaker';" | mysql

echo "CREATE DATABASE beaker_migration_test;" | mysql
echo "GRANT ALL ON beaker_migration_test.* TO 'beaker'@'localhost' IDENTIFIED BY
'beaker';" | mysql
