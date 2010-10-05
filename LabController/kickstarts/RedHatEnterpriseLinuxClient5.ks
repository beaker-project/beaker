#if $varExists('sysprofile')
#set listed_snippet_profiles = $getVar('sysprofile','').split(';')
#for $snippet_profile in $listed_snippet_profiles
# Snippet Profile: $snippet_profile
$SNIPPET($snippet_profile)
#end for
#else
#if $varExists('method') and $mgmt_parameters.has_key("method_%s" % $method) and \
 $tree.find("nfs://") != -1
$SNIPPET("install_method")
#else
## Do it the way the tree was imported
url --url=$tree
#end if

#if $getVar('system_name', '') != '' and $getVar('manual', 'False') == 'False'
auth  --useshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr #slurp
#if $getVar('kernel_options_post','') != ''
    --append="$kernel_options_post"
#end if

#if $getVar('rhts_server', '') != ''
## Use text mode install
text
key $getVar('key', '7fcc43557e9bbc42')
#else
## For normal provisioning use Workstation key
key $getVar('key', 'da3122afdb7edd23')
#end if

$getVar('mode', '')

$SNIPPET("network")
## Firewall configuration
## firewall in kickstart metadata will enable the firewall
## firewall=22:tcp,80:tcp will enable the firewall with ports 22 and 80 open.
## always allow port 12432 so that beah harness will support multihost
firewall #slurp
#if $getVar('firewall', 'disabled') == 'disabled':
--disabled
#else
--enabled --port=12432:tcp #slurp
#if $getVar('firewall', '') != '':
,$getVar('firewall')
#end if
#end if

#if $getVar('rhts_server', '') != ''
# Don't Run the Setup Agent on first boot
firstboot --disable
#end if

# System keyboard
keyboard $getVar('keyboard', 'us')
# System language
lang $getVar('lang','en_US.UTF-8')
$yum_repo_stanza
reboot
#Root password
rootpw --iscrypted $getVar('password', $default_password_crypted)
# SELinux configuration
selinux $getVar('selinux','--enforcing')

# Configure the X Window System
#if $getVar('rhts_server','') != '' or $getVar('skipx','') != ''
skipx
#else
xconfig --startxonboot
#end if

# System timezone
timezone  $getVar('timezone', 'America/New_York')
# Install OS instead of upgrade
install

## Add Optional repos
#if $getVar('tree_repos','') != ''
#for $repo in $getVar('tree_repos','').split(':')
#if $repo.find(",") != -1
#set (reponame, repourl) = $repo.split(',',1)
repo --name=$reponame --baseurl=http://$server/distros$repourl
#end if
#end for
#end if

$SNIPPET("rhts_scsi_ethdevices")
$SNIPPET("rhts_partitions")
$SNIPPET("RedHatEnterpriseLinuxClient5")
$SNIPPET("system")

%packages --resolvedeps --ignoremissing
#if $getVar('rhts_server', '') == ''
@admin-tools
@base
@base-x
@core
@dialup
@editors
@games
@gnome-desktop
@graphical-internet
@graphics
@java
@office
@printing
@sound-and-video
@text-internet
busybox
comps-extras
cracklib-dicts
gnome-mime-data
iso-codes
kernel-headers
nash
rmt
tzdata
xkeyboard-config
#end if
$SNIPPET("rhts_packages")

#end if
#end if
%pre
$SNIPPET("rhts_pre")
$SNIPPET("RedHatEnterpriseLinuxClient5_pre")
$SNIPPET("system_pre")

%post
$SNIPPET("rhts_post")
$SNIPPET("RedHatEnterpriseLinuxClient5_post")
$SNIPPET("system_post")

#if $getVar('ks_appends', '') != '':
$SNIPPET("ks_appends")
#end if
