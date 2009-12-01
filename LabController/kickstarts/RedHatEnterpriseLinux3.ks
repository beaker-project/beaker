url --url=$tree
#if $getVar('system_name', '') != '' and $getVar('manual', 'False') == 'False'
authconfig  --enableshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr
# Use text mode install
text
$SNIPPET("network")
# Firewall configuration
firewall --disabled
# Run the Setup Agent on first boot
firstboot --disable
# System keyboard
keyboard us
mouse none
# System language
lang $getVar('lang','en_US.UTF-8')
langsupport --default $getVar('lang', 'en_US.UTF-8') $getVar('lang','en_US.UTF-8')
$yum_repo_stanza
reboot
#Root password
rootpw --iscrypted $getVar('password', $default_password_crypted)
#if $getVar('skipx','') != ''
# Do not configure the X Window System
skipx
#end if
# System timezone
timezone  America/New_York
# Install OS instead of upgrade
install

$SNIPPET("RedHatEnterpriseLinux3")
$SNIPPET("rhts_scsi_ethdevices")
$SNIPPET("rhts_partitions")

%packages --resolvedeps --ignoremissing
$SNIPPET("rhts_packages")

#end if
%pre
PATH=/usr/bin:$PATH
$SNIPPET("RedHatEnterpriseLinux3_pre")
$SNIPPET("rhts_pre")

%post
PATH=/usr/bin:$PATH
$SNIPPET("RedHatEnterpriseLinux3_post")
$SNIPPET("rhts_post")
