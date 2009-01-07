url --url=$tree
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
# SELinux configuration
selinux --enforcing
# Do not configure the X Window System
skipx
# System timezone
timezone  America/New_York
# Install OS instead of upgrade
install

network --bootproto=dhcp

$SNIPPET("main_partition_select")
$SNIPPET("main_packages_select")

%pre
$kickstart_start
$SNIPPET("rhts_pre_partition_select")
$SNIPPET("pre_packages_select")

%post
$yum_config_stanza
$SNIPPET("rhts_post_install_kernel_options")
$kickstart_done
$SNIPPET("rhts_recipe")
