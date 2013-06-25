.. title:: Beaker help

Resources
=========

.. container:: resourcesbox

   .. raw:: html

      <h3>for users</h3>

   .. toctree::
      :maxdepth: 1

      user-guide/index
      man/index
      Release notes <whats-new/index>
      glossary

   * `Beaker Quick Start Guide: slides (PDF) <psss-beaker-quick-start-guide-slides.pdf>`__
   * `RELAX NG schema for Beaker jobs <schema/beaker-job.rng>`__

.. container:: resourcesbox

   .. raw:: html

      <h3>for administrators</h3>

   * `Beaker in a box (10 minute quick start) <../in-a-box/>`_

   .. toctree::
      :maxdepth: 1

      admin-guide/index

   * `Migrating from Cobbler (pre-Beaker 0.9) <../cobbler-migration.html>`_

.. container:: resourcesbox

   .. raw:: html

      <h3>for developers</h3>

   .. toctree::
      :maxdepth: 1

      Beaker server API documentation <server-api/index>
      alternative-harnesses/index

Search this site
================

.. raw:: html

   <div id="cse-search-form" style="width: 100%;">Loading…</div>
   <script src="http://www.google.com/jsapi" type="text/javascript"></script>
   <script type="text/javascript"> 
     google.load('search', '1', {language : 'en', style : google.loader.themes.MINIMALIST});
     google.setOnLoadCallback(function() {
       var customSearchOptions = {};
       customSearchOptions['adoptions'] = {'layout': 'noTop'};
       var customSearchControl = new google.search.CustomSearchControl(
         '000379057217241479047:jjwkmhjefoc', customSearchOptions);
       customSearchControl.setResultSetSize(google.search.Search.FILTERED_CSE_RESULTSET);
       var options = new google.search.DrawOptions();
       options.setAutoComplete(true);
       options.enableSearchboxOnly("http://beaker-project.org/search.html");
       customSearchControl.draw('cse-search-form', options);
     }, true);
   </script>

Getting further help
====================

The best way to interact with Beaker developers and users is in the `#beaker 
<irc://chat.freenode.net/beaker>`_ IRC channel on irc.freenode.net. The Beaker 
developers monitor this channel, and development discussions often happen 
there. Alternatively, you can post your question to the `beaker-devel 
<https://fedorahosted.org/mailman/listinfo/beaker-devel>`_ mailing list.

If you've found a bug in Beaker, please report it in `Red Hat Bugzilla 
<https://bugzilla.redhat.com/enter_bug.cgi?product=Beaker>`__ against the 
Beaker product.
