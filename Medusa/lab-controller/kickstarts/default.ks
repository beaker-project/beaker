url --url=$tree
auth  --useshadow  --enablemd5
# System bootloader configuration
bootloader --location=mbr
# Use text mode install
text
# Firewall configuration
firewall --enabled
# Run the Setup Agent on first boot
firstboot --disable
# System keyboard
keyboard $getVar('keyboard', 'us')
# System language
lang $getVar('lang','en_us')
$yum_repo_stanza
reboot
#Root password
rootpw --iscrypted $getVar('password', '\$1\$mF86/UHC\$WvcIcX2t6crBz2onWxyac.')
# SELinux configuration
selinux $getVar('selinux','--enforcing')
# Do not configure the X Window System
skipx
# System timezone
timezone  $getVar('timezone', 'America/New_York')
# Install OS instead of upgrade
install
network --bootproto=dhcp

$SNIPPET("rhts_partitions")

%packages --resolvedeps --ignoremissing
$SNIPPET("rhts_packages")

%pre
$SNIPPET("rhts_pre")

%post
$SNIPPET("rhts_post")
