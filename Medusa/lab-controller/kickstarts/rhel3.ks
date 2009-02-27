url --url=$tree
#if $getVar('system_name', '') != ''
authconfig  --enableshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr
# Use text mode install
text
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
rootpw --iscrypted \$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.
# Do not configure the X Window System
skipx
# System timezone
timezone  America/New_York
# Install OS instead of upgrade
install

network --bootproto=dhcp

$SNIPPET("rhts_partitions")

%packages --resolvedeps --ignoremissing
$SNIPPET("rhts_packages")

#end if
%pre
$SNIPPET("rhts_pre")

%post
$SNIPPET("rhts_post")
