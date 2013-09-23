#!/bin/bash

# On Fedora, this script installs the necessary packages, sets up the database
# and copies selenium JAR to the appropriate location. All of these
# are needed to run Beaker's test suite.

# You should run this as root from the Misc/ directory of a git clone
# of the source repository

# Abort if any of these fails
set -e

# install wget
yum -y install wget python-sphinx-1.1.3-8.fc20.beaker.1

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

# Download selenium JAR
mkdir -p /usr/local/share/selenium
pushd /usr/local/share/selenium
wget http://selenium.googlecode.com/files/selenium-server-standalone-2.35.0.jar
popd


# make build
pushd ../
make build
popd

