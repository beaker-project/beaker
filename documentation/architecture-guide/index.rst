.. _architecture-guide:

Architecture Guide
==================


Scope of document
-----------------

This document aims to provide an in-depth exploration of Beaker concepts and
its inner workings, from the way it handles permissions, to the operation of
the automated scheduler, to the way it handles system provisioning.

.. note::

   While that is the eventual aim of this guide, it is currently a work in
   progress, offering only a broad overview of these capabilities. Over time
   additional details will be added, providing further insight into the
   details of the various features.


Audience
--------

This guide is primarily aimed at developers working directly on Beaker.
However, the presentation doesn't assume the reader is a programmer, so it
should still be useful for users wanting a more in-depth understanding of
what Beaker is doing on their behalf, and Beaker administrators wanting
a greater understanding of the service the tool is intended to provide.


Contents
--------

.. toctree::
   :maxdepth: 2

   capabilities
   provisioning-process
   job-monitoring
   log-storage
   beaker-differences
