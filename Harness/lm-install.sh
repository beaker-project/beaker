#!/bin/bash -x

(

function usage()
{
  cat<<END
Usage:       $0 [-h|--help|HOST]
Description: Pack and copy Harness to a given lab-machine.
             Uses scp to copy file to directory defined by LM_INSTALL_ROOT.
             This directory must exist, as scp does not create intermediate
             directories.
Note!        If LABM environment variable is not set, HOST must be provided.
             Anything apart from '-h' and '--help' is considered a hostname.
END
}

case "$1" in
--help|-h|-?)
  usage
  exit 0
  ;;
esac

################################################################################
# CHECKS:
################################################################################

LABM="${1:-"$LABM"}"
if [[ -z "$LABM" ]]; then
  echo -e "ERROR: HOST or LABM must be set!\n" >&2
  usage >&2
  exit 1
fi

################################################################################
# SET-UP:
################################################################################
export BEAH_DEV=".dev$(date "+%Y%m%d%H%M")"

if [[ -f "$LM_INSTALL_ENV" ]]; then
  . "$LM_INSTALL_ENV"
elif [[ -r "lm-install-env.sh.tmp" ]]; then
  . lm-install-env.sh.tmp
else
  . lm-install-env.sh
fi

TEMPLATE_DIR=lm-install
echo "Pre-check of environment variables:"
( ${TEMPLATE_DIR}/install/lm-install.sh --env-check; )

LM_INSTALL_ROOT="${LM_INSTALL_ROOT:-"/tmp/lm-install"}"
DISTRO_ROOT="${DISTRO_ROOT:-"/tmp/lm-install"}"

################################################################################
# INIT:
################################################################################
rm -rf $DISTRO_ROOT/
mkdir -p $DISTRO_ROOT/install

################################################################################
# BUILD SDIST:
################################################################################
python setup.py sdist
cp dist/beah-0.1.a1${BEAH_DEV}.tar.gz $DISTRO_ROOT/install/

################################################################################
# WRITE FILES:
################################################################################
cp -R -t $DISTRO_ROOT/ ${TEMPLATE_DIR}/*
chmod 755 $DISTRO_ROOT/install/lm-install.sh

cat >$DISTRO_ROOT/install/env.sh <<END
LM_INSTALL_ROOT="${LM_INSTALL_ROOT}"
LAB_CONTROLLER="${LAB_CONTROLLER:-http://localhost:5222/}"
BEAKER_HOSTNAME="${BEAKER_HOSTNAME:-$LABM}"
LM_RHTS_REPO="${LM_RHTS_REPO}"
LM_YUM_FILE="${LM_YUM_FILE}"
LM_YUM_PATH="${LM_YUM_PATH}"
LM_FAKELC="${LM_FAKELC}"
FAKELC_SERVICE="${FAKELC_SERVICE}"

BEAH_DEV="${BEAH_DEV}"
END

(
. $DISTRO_ROOT/install/env.sh
echo "Check of environment variables:"
${TEMPLATE_DIR}/install/lm-install.sh --env-check
)

cat >$DISTRO_ROOT/main.sh <<END
pushd ${LM_INSTALL_ROOT}
. ./install/env.sh
. ./install/lm-install.sh check
popd
lm_main "\${1:-"help"}"
END

LM_PACKAGE_FILE=lm-package${BEAH_DEV}.sh
LM_PACKAGE=/tmp/$LM_PACKAGE_FILE
cat >${LM_PACKAGE} <<END
#!/bin/sh
base64 -d <<FILE_END | tar xjC ${LM_INSTALL_ROOT}
$(tar cjC ${DISTRO_ROOT} . | base64)
FILE_END
. ${LM_INSTALL_ROOT}/main.sh "\$@"
END
chmod 755 ${LM_PACKAGE}
scp ${LM_PACKAGE} root@${LABM}:${LM_INSTALL_ROOT}
rm ${LM_PACKAGE}

echo -e "\nRun '${LM_INSTALL_ROOT}/${LM_PACKAGE_FILE}' on lab-machine ${LABM} and follow instructions."

################################################################################
# CLEAN-UP:
################################################################################
rm -rf $DISTRO_ROOT/

)

