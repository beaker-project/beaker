Failed recipes linked in email notification
===========================================

Beaker now provides a hyperlink to display associated failed recipe results
within job notification emails.

For example, Beaker previously included the OSVersion for the recipe in
the notification.

``RecipeID: 14304 Arch: x86_64 System: dev-kvm-guest-10.rhts.eng.bos.redhat.com
Distro: RHEL-6.7-20150702.0 OSVersion: RedHatEnterpriseLinux6.7
Status: Completed Result: Fail``

Beaker now provides the result notification in the format:

``RecipeID: 14304 Arch: x86_64 System: dev-kvm-guest-10.rhts.eng.bos.redhat.com
Distro: RHEL-6.7-20150702.0 Status: Completed Result: Fail
<https://beaker-devel.app.eng.bos.redhat.com/recipes/14304>``

(Contributed by Blake McIvor in :issue:`1326968`.)


