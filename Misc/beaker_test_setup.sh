#!/bin/bash

# This script installs the necessary packages, sets up the database
# and copies selenium JAR to the appropriate location. All of these
# are needed to run Beaker's test suite.

# Tested on Fedora 18
# You should run this as root

# Abort if any of these fails
set -e

# Beaker server repository
wget -O /etc/yum.repos.d/beaker-server.repo http://beaker-project.org/yum/beaker-server-Fedora.repo

# Find the dependencies
yum deplist beaker-server beaker-lab-controller beaker-integration-tests beaker-client beaker | grep 'provider' | grep -v 'beaker*' | awk '{print $2'} | sort -u > beaker_deplist

# Need this for doing a make which sets up the path for the integration
# TODO: Perhaps worth fixing this.
echo "python-sphinx" >> beaker_deplist
echo "git" >> beaker_deplist
echo "mysql-server" >> beaker_deplist

# Install them
while read line
do
    yum -y install `yum info $line | grep 'Name' | awk '{print $3}'`
done <beaker_deplist

#setup mysql
cp /etc/my.cnf /etc/my.cnf-orig
cat /etc/my.cnf-orig | awk '
        {print $1};
        /\[mysqld\]/ {
            print "default-storage-engine=INNODB";
            print "max_allowed_packet=50M";
            print "character-set-server=utf8";
        }' > /etc/my.cnf
service mysqld restart
echo "CREATE DATABASE beaker_test;" | mysql
echo "GRANT ALL ON beaker_test.* TO 'beaker'@'localhost' IDENTIFIED BY
'beaker';" | mysql

# Download selenium JAR
mkdir -p /usr/local/share/selenium
pushd /usr/local/share/selenium
wget http://selenium.googlecode.com/files/selenium-server-standalone-2.33.0.jar
popd
