# LM_INSTALL_ROOT - directory on lab machine(LM) where to copy files to.
# Optional. Defaults to /tmp/lm-install
#LM_INSTALL_ROOT=/tmp/lm-install

# LAB_CONTROLLER - address of labcontroller (LC).
# Optional. Defaults to localhost:5222 (on LM)
#LAB_CONTROLLER="http://$HOSTNAME:5222/"

# LM_FAKELC - if set, start beah-fakelc on LM. (use default LAB_CONTROLLER
# setting with this option.)
#LM_FAKELC=1

# BEAKER_HOSTNAME - the name used by LM to introduce iteslf to LC.
# Optional. Defaults to $HOSTNAME
#BEAKER_HOSTNAME="pure-virtual"

# LM_RHTS_REPO - path to yum repository containing RHTS tests.
# Conditionally mandatory. Required for using RHTS test.
#LM_RHTS_REPO="http://examples.com/rhts/repo/noarch"

# LM_YUM_PATH and LM_YUM_FILE - path and filename of yum rpm.
# Conditionally mandatory. This is not necessary on fedora, but is required on
# some ancient RHEL`s.
#LM_YUM_PATH=http://examples.com/beaker
#LM_YUM_FILE=yum-2.2.2-1.rhts.EL4.noarch.rpm

