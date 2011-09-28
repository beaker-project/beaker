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

key --skip

#if $getVar('system_name', '') != '' and $getVar('manual', 'False') == 'False'
# System bootloader configuration
bootloader --location=mbr #slurp
#if $getVar('kernel_options_post','') != ''
    --append="$kernel_options_post"
#end if

$getVar('mode', 'cmdline')

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
#if $getVar('skipx','') != ''
skipx
#else
#if not $getVar('arch','').startswith('s390')
xconfig --startxonboot
#end if
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
repo --name=$reponame --cost=100 --baseurl=http://$server/distros$repourl
#end if
#end for
#end if

$SNIPPET("rhts_devices")
$SNIPPET("rhts_partitions")
$SNIPPET("RedHatEnterpriseLinux6")
$SNIPPET("system")

%packages --ignoremissing #slurp
#if $getVar('packages', '') == '':
--default
#else

$SNIPPET("rhts_packages")
#end if ## if packages

#end if ## manual

#end if ## sysprofile snippet

%pre --log=/dev/console
$SNIPPET("rhts_pre")
$SNIPPET("RedHatEnterpriseLinux6_pre")
$SNIPPET("system_pre")

%post --log=/dev/console
$SNIPPET("rhts_post")
$SNIPPET("RedHatEnterpriseLinux6_post")
$SNIPPET("system_post")

#if $getVar('ks_appends', '') != '':
$SNIPPET("ks_appends")
#end if
