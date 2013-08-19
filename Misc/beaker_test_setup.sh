#!/bin/bash

# This script installs the necessary packages, sets up the database
# and copies selenium JAR to the appropriate location. All of these
# are needed to run Beaker's test suite.

# Tested on Fedora 19+20
# You should run this as root

# Abort if any of these fails
set -e

# create beaker RPMs

pushd ../

yum-builddep -y beaker.spec
yum -y install tito createrepo
tito build --test --rpm
createrepo --no-database /tmp/tito/noarch

cat >/etc/yum.repos.d/beaker-local-builds.repo <<"EOF"
[tito]
name=tito
baseurl=file:///tmp/tito/noarch/
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
