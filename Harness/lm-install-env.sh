# LM_INSTALL_ROOT - directory on lab machine(LM) where to copy files to.
# Optional. Defaults to /tmp/lm-install
#LM_INSTALL_ROOT=/tmp/lm-install

# LAB_CONTROLLER - address of labcontroller (LC).
# Optional. Defaults to localhost:5222 (on LM)
#LAB_CONTROLLER="http://$HOSTNAME:5222/"

# LM_FAKELC - if set, start beah-fakelc on LM. (use default LAB_CONTROLLER
# setting with this option.)
#LM_FAKELC=1

# FAKELC_SERVICE - if set, use beah-fakelc as a service.
#FAKELC_SERVICE=1

# BEAH_NODEP - tweak in setup.py to avoid checking dependencies.
#BEAH_NODEP=1

# LM_EXPORT - format of package to create. bin or bz2. Default: bin.
# base64 on RHEL5.4 does not understand files created with base64 on F11
#LM_EXPORT=bz2
# BEAKER_HOSTNAME - the name used by LM to introduce iteslf to LC.
# Optional. Defaults to $HOSTNAME
#BEAKER_HOSTNAME="pure-virtual"

# LM_NO_RHTS - do not use RHTS repos if set. (Useful during offline testing.)
#LM_NO_RHTS=1

# LM_RHTS_DEVEL_REPO - path to yum repository containing RHTS scripts.
# Conditionally mandatory. Required for using RHTS test.
#LM_RHTS_DEVEL_REPO="http://examples.com/rhts/devel"

# OBSOLETE: Repository containing tests should be provided by recipe.
## LM_RHTS_REPO - path to yum repository containing RHTS tests.
## Conditionally mandatory. Required for using RHTS test.
##LM_RHTS_REPO="http://examples.com/rhts/repo/noarch"

# LM_YUM_PATH and LM_YUM_FILE - path and filename of yum rpm.
# Conditionally mandatory. This is not necessary on fedora, but is required on
# some ancient RHEL`s.
#LM_YUM_PATH=http://examples.com/beaker
#LM_YUM_FILE=yum-2.2.2-1.rhts.EL4.noarch.rpm

