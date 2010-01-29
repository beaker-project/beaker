#!/bin/bash

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

if [[ "$0" == "dev-env.sh" ]]; then
	echo "*** This script should be sourced \". $0\" not executed." >&2
	exit 1
fi

function file_path()
(
        [[ -n "$2" ]] && cd "$2"
        local path="$(dirname "$1")"
        [[ -n "$path" ]] && cd $path &>/dev/null
        echo $PWD
)

function script_path()
{
        file_path "${BASH_SOURCE[0]}"
}

################################################################################
# SETUP:
################################################################################
export BEAH_DIR="$(script_path)"

export BEAHLIB_ROOT=$BEAH_DIR

export PATH=$PATH:$BEAH_DIR/bin:$BEAH_DIR/beah/bin
export PYTHONPATH=$PYTHONPATH:$BEAH_DIR

# Path to search for config files:
export BEAH_ROOT=$BEAH_DIR

# If present use developmental .tmp conf files (``.tmp'' is used to match
# .gitignore)
if [[ -f $BEAH_DIR/beah.conf.tmp ]]; then
        export BEAH_CONF=$BEAH_DIR/beah.conf.tmp
fi
if [[ -f $BEAH_DIR/beah_beaker.conf.tmp ]]; then
        export BEAH_BEAKER_CONF=$BEAH_DIR/beah_beaker.conf.tmp
fi

################################################################################
# FUNCTIONS:
################################################################################
function beah() { python $BEAH_ROOT/beah/bin/cli.py "$@"; }
function beah-srv() { python $BEAH_ROOT/beah/bin/srv.py "$@"; }
function beah-out-backend() { $BEAH_ROOT; python $BEAH_ROOT/beah/bin/out_backend.py "$@"; }
function beah-cmd-backend() { python $BEAH_ROOT/beah/bin/cmd_backend.py "$@"; }
function fakelc() { python $BEAH_ROOT/beah/tools/fakelc.py; }
function beah-beaker-backend() { python $BEAH_ROOT/beah/backends/beakerlc.py; }
function beah-fwd-backend() { python -c "from beah.backends.forwarder import main; main()"; }
function beah-rhts-task() { python -c "from beah.tasks.rhts_xmlrpc import main; main()"; }
function inst1() { if [[ ! -z "$LABM1" ]]; then inst_all $LABM1; fi }
function inst2() { if [[ ! -z "$LABM2" ]]; then inst_all $LABM2; fi }
function inst3() { if [[ ! -z "$LABM3" ]]; then inst_all $LABM3; fi }
function inst4() { if [[ ! -z "$LABM4" ]]; then inst_all $LABM4; fi }
function inst5() { if [[ ! -z "$LABM5" ]]; then inst_all $LABM5; fi }
function _labms()
{
  if [[ ! -z "$1" ]]; then
    echo -n "$1 "
  fi
}
function labms()
{
  for i in $*; do
    eval "_labms \"\$LABM$i\""
  done
  echo
}

function lmcall()
{
  local lms=
  local append=
  while [[ ! -z "$1" ]]; do
    case "$1" in
      -m)
        shift
        lms="$lms $1"
        shift
        ;;
      -a)
        shift
        append="$append $1"
        shift
        ;;
      -n)
        shift
        append="$append $(labms $1)"
        shift
        ;;
      --)
        shift
        break
        ;;
      -*)
        echo "--- ERROR: Unknow option $1" >&2
        return 1
        ;;
      *)
        break
        ;;
    esac
  done
  for labm in ${lms:-$LABMS} $append; do
    LABM=$labm "$@"
  done
}

function xlm()
{
  TITLE=$LABM xt
}

function gxlm()
{
  lmcall "$@" xlm
}

function inst_all()
{
  pushd $BEAH_ROOT
  lmcall "$@" ./lm-install.sh
  popd
}
function pwdless()
{
  ssh root@$LABM mkdir -p .ssh
  cat ~/.ssh/id_rsa.pub | ssh root@$LABM 'cat >> .ssh/authorized_keys'
}
function gpwdless()
{
  lmcall "$@" pwdless
}
function launcher()
(
  default="s o l"
  all="s o c"

  function view_logs()
  {
    local server=log_list
    if ! { gvim --serverlist | grep -i $server; }; then
      gvim --servername $server --remote /tmp/logs
      gvim --servername $server --remote-send ":set readonly nomodifiable<CR>gh"
    fi
  }

  function xt()
  {
    a1=$1
    eval "temp=\$running_$a1"
    if [[ -n $temp ]]; then
      return 1
    fi
    eval "running_$a1=1"
    shift

    local geo=$1
    shift

    if [[ -z "$redir" ]]; then
      xterm -geometry $geo -title "$*" -n "$*" -e "$@" &
    else
      # FIXME: this does not work properly! I would like to see
      # output in runtime...
      xterm -geometry $geo -title "$*" -n "$*" -e redir "beah_${a1}_$(date +%Y%m%d_%H%M%S)" "$@" &
    fi
  }

  function runner()
  {
    if [[ -n "$redir" ]]; then
      view_logs
    fi
    for i in $@; do
      case $i in
        a|A) runner $all ;;
        s|S) xt s 80x35-0-0 beah-srv & ;;
        c|C) xt c 80x20+0+0 beah-cmd-backend & ;;
        o|O) xt o 80x35-0+0 beah-out-backend & ;;
        l|L) xt l 80x20+0-0 fakelc & ;;
        b|B) sleep 2 && # beaker backend should wait for fakelc.
             xt b 80x20+0+0 beah-beaker-backend & ;;
      esac
    done
  }

  cd $BEAH_ROOT

  if [[ "$1" == "-r" || "$1" == "--redir" ]]; then
    redir=1
    shift
  fi
  if [[ -z "$@" ]]; then
    runner $default
  elif [[ "$1" == '-h' || "$1" == '--help' ]]; then
    cat <<END
USAGE: launcher [-r|--redir] [-h|--help] [ (a|s|o|c|l|b) ... ]
OPTIONS:
  -r --redir - redirect all output to files
  -h --help  - display this message
COMMANDS:
  s - start the controller - srv
  c - start the command backend - cmd_backend
  o - start the output backend - out_backend
  a - start all three programs
    - if no arguments are provided, start server and output backend
  l - start fake lab controller
  b - start beaker backend
NOTE: programs are started in separate xterm windows

END
  else
    runner $@
  fi
)

FUNCTIONS="$(echo "beah"{,-srv,-{out,cmd,beaker}-backend}) launcher fakelc inst_all"
export -f $FUNCTIONS

cat <<END
** Environment is set. **
Run ${FUNCTIONS/ /, }
END

