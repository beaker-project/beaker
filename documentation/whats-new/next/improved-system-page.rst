Improved system page
====================

In this release the system page has been re-arranged and improved. The aim of 
the improvements is to reduce wasted space, convey information more 
efficiently, and simplify interactions with the page.

Important changes you need to be aware of are listed below. For a complete 
description of all the changes and their background and rationale, refer to the 
:ref:`original design proposal <beakerdev:proposal-system-page-improvements>`.

Major page layout changes
-------------------------

The system form — the set of fields arranged in two columns at the top of the 
system page — has historically formed the focus of the system page. Over many 
years of development, however, it has grown into a disorganized assortment of 
data, of which only a small amount is relevant for any given workflow on the 
page.

In its place, the system page now has three "quick info boxes". They are 
designed to show the most important facts about the system and to give quick 
access to the most common operations, while occupying a very small amount of 
vertical space. The left-hand box shows a summary of the system's hardware. The 
middle box shows a summary of the system's current usage. The right-hand box 
shows a summary of the system's health.

The interface elements previously contained in the system form will instead be 
shown in tabs below. The previous horizontal tab strip is replaced with 
a vertical list of tabs, to accommodate their increasing number. The tabs have 
also been re-ordered and grouped by theme.

Relocated interface elements
----------------------------

The various fields and interface elements which previously made up the system 
form are now grouped into more appropriate tabs on the page:

* The :guilabel:`Lab Controller`, :guilabel:`Location`, :guilabel:`Lender`, and
  :guilabel:`Kernel Type` fields are part of the :guilabel:`Hardware 
  Essentials` tab.

* The :guilabel:`Hypervisor` field (renamed :guilabel:`Host Hypervisor` for
  clarity), as well as the :guilabel:`Vendor`, :guilabel:`Model`, 
  :guilabel:`Serial Number`, and :guilabel:`MAC Address` fields, are included 
  in the :guilabel:`Hardware Details` tab.

* The :guilabel:`Owner` and :guilabel:`Notify CC` fields are located on a new
  :guilabel:`Owner` tab.

* The :guilabel:`Loan Settings` modal, plus the :guilabel:`Request Loan`
  functionality previously accessible through the :guilabel:`Contact Owner` 
  button, have been moved to a dedicated :guilabel:`Loan` tab.

* The :guilabel:`Condition` and :guilabel:`Type` fields are part of the
  :guilabel:`Scheduler Settings` tab.

* Change a system's FQDN by clicking :guilabel:`Rename` in the page header.

The :guilabel:`Arch(s)` tab, for specifying supported architectures for the
system, has been replaced by the :guilabel:`Supported Architectures` field on 
the :guilabel:`Hardware Essentials` tab.

:guilabel:`Provision` tab always provisions
-------------------------------------------

The :guilabel:`Provision` tab now always provisions the system immediately (if 
you have permission to do so). In previous versions of Beaker, the tab would 
sometimes schedule a new job for the system instead of provisioning it 
immediately, depending on the current state of the system.

To provision a system through the scheduler, use the reserve workflow. The 
:guilabel:`Provision` tab now includes a direct link to the reserve workflow 
for the specific system.

Screen scraping scripts will be impacted
----------------------------------------

The HTML structure of the system page has changed substantially in this 
release. In addition, a number of widgets render their markup entirely in the 
browser and no corresponding HTML appears in the server response. Therefore any 
screen scraping scripts which interact with the system page are likely to be 
impacted.

Since Beaker 0.15 a number of new Beaker client subcommands for manipulating 
systems have been added, to reduce the need for screen scraping scripts. You 
should use these in preference to screen scraping whenever possible:

* :ref:`policy-list <bkr-policy-list>`, :ref:`policy-grant <bkr-policy-grant>`,
  and :ref:`policy-revoke <bkr-policy-revoke>`: for listing, adding, and 
  removing rules from system access policies

* :ref:`loan-grant <bkr-loan-grant>` and :ref:`loan-return <bkr-loan-return>`:
  for granting and returning system loans

* :ref:`system-status <bkr-system-status>` and :ref:`system-modify
  <bkr-system-modify>`: for viewing and setting certain system attributes 
  (currently just owner and condition)

If you have screen scraping scripts whose functionality is not covered by these 
subcommands, please `file an RFE against Beaker 
<https://bugzilla.redhat.com/enter_bug.cgi?product=Beaker&keywords=FutureFeature>`__ 
requesting a new client command exposing the functionality you need.

Bugs fixed
----------

The following user interface bugs/RFEs are solved by the system page 
improvements:

* :issue:`619335`: The :guilabel:`Provision` tab should offer a way of
  filtering distros, to make it easier to find the desired distro.
* :issue:`692777`: The system page should show how long a system has been
  reserved.
* :issue:`880724`: The reserve workflow does not filter systems by lab
  controller, even if you select a specific lab controller when filtering for 
  distro trees.
* :issue:`884399`: When using the :guilabel:`Provision` tab, any install
  options given are applied on top of the default install options for that 
  system and distro. As a consequence, if you edit the pre-populated install 
  options on the :guilabel:`Provision` tab to *remove* a default option, it 
  will have no effect.
* :issue:`980352`: No error message is shown if a validation error occurs when
  editing a system (for example, when the condition report value is too long).
* :issue:`999444`: The :guilabel:`Loan Settings` button appears when editing
  a system, but clicking it does nothing.
* :issue:`1009323`: If a user has no permission to edit a system, clicking the
  :guilabel:`Edit system` button or the :guilabel:`Change` button for notify cc 
  redirects the user back to the system list, instead of to the original system 
  page.
* :issue:`1011284`: The :guilabel:`Loan Settings` button disappears after
  returning an existing loan.
* :issue:`1011293`: The loan settings modal offers to return a loan even when
  none exists.
* :issue:`1020107`: After changing loan settings and closing the loan settings
  modal, the system page does not reflect the new state of the system. In 
  particular, if a user loans the system to themselves they should then be 
  permitted to take the system, but the :guilabel:`Take` button does not 
  appear.
* :issue:`1037280`: The meaning of the :guilabel:`Hypervisor` field on the
  system page is not clear.
* :issue:`1059535`: When saving changes on the :guilabel:`Power Config` tab,
  all fields are recorded in the system activity as being changed, even if they 
  were not actually changed.
* :issue:`1062086`: When using the reserve workflow, if the user selects
  a combination of options which cannot be satisfied by any systems, Beaker 
  warns about the situation but then schedules the job anyway.
* :issue:`1062706`: The procedure for "taking" an Automated system is awkward
  and requires too many steps.
* :issue:`1070036`: When saving changes on the :guilabel:`Power Config` tab, if
  a validation error occurs all fields are cleared and the values are lost.
* :issue:`1134689`: Under some circumstances when saving changes on the
  :guilabel:`Access Policy` tab, a rule is recorded as removed and added 
  multiple times for no reason.
