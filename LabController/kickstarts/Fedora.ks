url --url=$tree
#if $getVar('system_name', '') != ''
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
lang $getVar('lang','en_us.UTF-8')
$yum_repo_stanza
reboot
#Root password
rootpw --iscrypted $getVar('password', $default_password_crypted)
# SELinux configuration
selinux $getVar('selinux','--enforcing')
# Do not configure the X Window System
skipx
# System timezone
timezone  $getVar('timezone', 'America/New_York')
# Install OS instead of upgrade
install

$SNIPPET("Fedora")
$SNIPPET("rhts_devices")
$SNIPPET("rhts_partitions")

%packages --ignoremissing
$SNIPPET("rhts_packages")

#end if
%pre
$SNIPPET("Fedora_pre")
$SNIPPET("rhts_pre")

%post
$SNIPPET("Fedora_post")
$SNIPPET("rhts_post")
