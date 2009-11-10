#!/bin/bash

function warning() { echo "--- WARNING: $*" >&2; }
function soft_error() { echo "--- ERROR: $*" >&2; return 1; }
function error() { echo "--- ERROR: $*" >&2; exit 1; }

function hgrep()
{
  history | grep "$@"
}

function psgrep()
{
  ps -ef | grep "$@"
}

function lm_env_check()
{
  ANSW=0
  if [[ -z "$BEAH_DEV" ]]; then
    soft_error "env.variable BEAH_DEV is not defined."
    ANSW=1
  fi
  if [[ -z "$LM_INSTALL_ROOT" ]]; then
    soft_error "env.variable LM_INSTALL_ROOT is not defined."
    ANSW=1
  fi
  if [[ -z "$LM_YUM_PATH" ]]; then
    warning "env.variable LM_YUM_PATH is not defined."
    ANSW=0
  fi
  if [[ -z "$LM_YUM_FILE" ]]; then
    warning "env.variable LM_YUM_FILE is not defined."
    ANSW=0
  fi
  if [[ -z "$LM_RHTS_REPO" ]]; then
    warning "env.variable LM_RHTS_REPO is not defined."
    ANSW=0
  fi
  return $ANSW
}
function lm_check()
{
  if lm_env_check; then
    if [[ ! -d "$LM_INSTALL_ROOT" ]]; then
      soft_error "Directory LM_INSTALL_ROOT does not exist!"
      return 2
    fi
    if [[ ! -r "$LM_INSTALL_ROOT/main.sh" ]]; then
      soft_error "File \$LM_INSTALL_ROOT/main.sh does not exist!"
      return 2
    fi
    true
  else
    return $?
  fi
}

function lm_pushd()
{
  mkdir -p $LM_INSTALL_ROOT/temp
  pushd $LM_INSTALL_ROOT/temp
}

function host_based_auth()
{
  # FIXME: find out how to do it!
  echo "FIXME: NotImplemented." >&2
  return 1
  #echo -e "\nHost *\n\tHostbasedAuthentication yes" >> /etc/ssh/ssh_config
}

function lm_install_yum()
{
  if rpm -q yum; then
    return 0
  fi
  lm_pushd
  /usr/bin/wget -N $LM_YUM_PATH/$LM_YUM_FILE
  /bin/rpm -Uvh $LM_YUM_FILE
  popd
}

function yumi()
{
  if rpm -q "$1"; then
    return 0
  fi
  yum -y install "$1"
}
function yummie()
{
  yum -y install "$@"
}

function lm_install_additional_packages()
{
  yummie vim-enhanced python
}

function lm_install_setuptools()
{
  lm_pushd
  case "${1:-"yum"}" in
  yum)
    yumi python-setuptools
    ;;
  src)
    wget http://pypi.python.org/packages/source/s/setuptools/setuptools-0.6c9.tar.gz
    tar xvzf setuptools-0.6c9.tar.gz
    pushd setuptools-0.6c9
    python setup.py install
    popd
    ;;
  egg)
    wget http://pypi.python.org/packages/2.6/s/setuptools/setuptools-0.6c9-py2.6.egg
    sh setuptools-0.6c9-py2.6.egg
    ;;
  *)
    soft-error "lm_install_setuptools do not understand '$1'"
    popd
    return 1
    ;;
  esac
  popd
}

function lm_install_beah()
{
  lm_pushd
    export BEAH_DEV

    if [[ -d "beah-0.1.a1${BEAH_DEV}" ]]; then
      echo "Directory \"beah-0.1.a1${BEAH_DEV}\" exists."
    else
      tar xvzf ${LM_INSTALL_ROOT}/install/beah-0.1.a1${BEAH_DEV}.tar.gz
    fi

    pushd beah-0.1.a1${BEAH_DEV}
      BEAH_RPM="dist/beah-0.1.a1${BEAH_DEV}-1.noarch.rpm"
      if [[ -f "$BEAH_RPM" ]]; then
        echo "RPM file \"$BEAH_RPM\" exists."
      else
        python setup.py bdist_rpm
      fi

      EGG_VER="$(python -V 2>&1 | cut -d " " -f 2 -s)"
      BEAH_EGG="dist/beah-0.1.a1${BEAH_DEV}-py$EGG_VER.egg"
      if [[ -f "$BEAH_EGG" ]]; then
        echo "Egg file \"$BEAH_EGG\" exists."
      else
        python setup.py bdist_egg
      fi

      case "${1:-"src"}" in
        rpm|-r|--rpm)
          yum -y install python-{zope-interface,twisted-{core,web},simplejson}
          rpm -iF "$BEAH_RPM"
          ;;
        yum|-y|--yum)
          yum -y install --nogpgcheck "$BEAH_RPM"
          ;;
        egg|-e|--egg)
          easy_install "$BEAH_EGG"
          ;;
        src|-s|--src)
          yum -y install python-{zope-interface,twisted-{core,web},simplejson}
          python setup.py install
          ;;
        build|-b|--build)
          ;;
        help|-h|-?|--help)
          echo "USAGE: $0 [src|egg|rpm|build|help]"
          ;;
        *)
          soft-error "lm_install_beah does not understand '$1'"
          echo "USAGE: $0 [src|egg|rpm|build|help]" >&2
          ;;
      esac
    popd
  popd
}

function lm_config_beah()
{
  cat > /etc/beah_beaker.conf <<END
[DEFAULT]
LAB_CONTROLLER=${LAB_CONTROLLER:-"http://localhost:5222/client"}

# PRETEND TO BE ANOTHER MACHINE:
HOSTNAME=${BEAKER_HOSTNAME:-"$HOSTNAME"}
END

  rm -f /etc/beah.conf.orig
  mv /etc/beah.conf /etc/beah.conf.orig
  sed -e 's/^DEVEL=.*$/DEVEL=True/' /etc/beah.conf.orig > /etc/beah.conf
}

function lm_tar_logs()
{
  tar cf $LM_INSTALL_ROOT/lm-logs.tar.gz /tmp/beah-*.out /var/log/beah*.log /tmp/var/log/rhts_task.log
}

function lm_logs()
{
  vim -o /tmp/beah-*.out /var/log/beah*.log /tmp/var/log/rhts_task.log
}

function lm_view_logs()
{
  view -o /tmp/beah-*.out /var/log/beah*.log /tmp/var/log/rhts_task.log
}

function lm_mon()
{
  while true; do
    ps -efH
    sleep 1
  done
}

function lm_stop()
{
  service beah-beaker-backend stop
  sleep 2
  if [[ -n "$LM_FAKELC" ]]; then
    kill -2 $(cat /tmp/beah-fakelc.pid)
  fi
  service beah-srv stop
}

function lm_restart()
{
  rm -rf /var/cache/rhts
  service beah-srv restart
  if [[ -n "$LM_FAKELC" ]]; then
    beah-fakelc &> /tmp/beah-fakelc.out &
    echo "$!" > /tmp/beah-fakelc.pid
    sleep 2
  fi
  service beah-beaker-backend restart
  lm_mon
}

function lm_kill()
{
  beah kill
  if [[ -n "$LM_FAKELC" ]]; then
    kill -2 $(cat /tmp/beah-fakelc.pid)
  fi
}

function lm_main_beah()
{
  lm_install_beah yum
  lm_config_beah
  if ! chkconfig beah-srv; then
    chkconfig --add beah-srv
  fi
  if ! chkconfig beah-beaker-backend; then
    chkconfig --add beah-beaker-backend
  fi
}

function lm_install_rhts_repo()
{
  # Add yum repository containing RHTS tests:
  cat > /etc/yum.repos.d/rhts-tests.repo << REPO_END
[rhts-noarch]
name=rhts tests development
baseurl=$LM_RHTS_REPO
enabled=1
gpgcheck=0
REPO_END
}

function lm_install_rhts_deps()
{
  lm_install_rhts_repo
  yummie rhts-test-env-lab rhts-legacy yum-utils
}

function lm_main_install()
{
  lm_install_yum
  lm_install_additional_packages
  lm_install_setuptools yum
  lm_main_beah
  lm_install_rhts_deps
}

function lm_main_run()
{
  lm_main_install
  lm_restart
  echo "Now you can run e.g. 'lm_kill', 'lm_restart' or 'lm_view_logs'."
  echo "Call 'lm_help' to display a help for these functions."
}

function lm_help()
{
cat <<END
lm_main_run
    Install all dependencies and run harness.
lm_restart
    Run harness. It runs lm_mon as the last command to monitor running procs.
lm_kill
    Send kill command to harness.
lm_stop
    Stops harness services. Use this if lm_kill does not work.
lm_logs
    View log files (uses vim).

OTHER FUNCTIONS:
lm_main [OPTION]
    Subroutine called on sourcing the script. See lm_main_help for usage.
lm_env_check
    Check environment variables.
lm_check
    Check environment including existence of $LM_INSTALL_ROOT/main.sh
lm_main_install
    Install dependencies, harness and rhts dependencies.
lm_main_beah
    Install harness.
lm_install_beah [OPTION]
    Install beah package.
    Options: 
      rpm -r --rpm   Install from built RPM file.
      yum -y --yum   Install from built RPM file using yum.
      egg -e --egg   Install from egg file.
      src -s --src   Install from source .tar.gz package.
END
}


function lm_main_help()
{
  cat <<END
Usage: $0 [OPTION]...

Options:
run | --run | -r
        install harness and dependencies and start services
check | --check | -c
        check environment variables and directories
env-check | --env-check | -e
        check environment variables
help | --help | -h | -?
        print this message

When used as:
  . $0 [ARGS]

END
echo "Now you can run e.g. 'lm_main_run', 'lm_main_beah' or 'lm_install_beah rpm'"
echo "Call 'lm_help' to display a help for these functions."
}

function lm_main()
{
case "${1:-"help"}" in
  env-check|--env-check|-e)
    lm_env_check
    ;;
  check|--check|-c)
    lm_check
    ;;
  install|--install|-i)
    if [[ -n "$LM_INSTALL_ROOT" && -d "$LM_INSTALL_ROOT/install" && -f "$LM_INSTALL_ROOT/install/env.sh" ]]; then
      . $LM_INSTALL_ROOT/install/env.sh
    fi
    lm_check && lm_main_install
    ;;
  run|--run|-r)
    if [[ -n "$LM_INSTALL_ROOT" && -d "$LM_INSTALL_ROOT/install" && -f "$LM_INSTALL_ROOT/install/env.sh" ]]; then
      . $LM_INSTALL_ROOT/install/env.sh
    fi
    lm_check && lm_main_run
    ;;
  help|--help|-h|-?)
    lm_main_help
    ;;
  *)
    soft_error "$0: Unrecognized option '$1'"
    lm_main_help
    ;;
esac
}

lm_main "$@"

