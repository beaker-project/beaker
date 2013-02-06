Alternative Harness Guide
=========================

This guide is for Beaker users who want to use a different harness than Beah in 
their recipes.

.. admonition:: These interfaces are currently provisional

   There may be minor backwards-incompatible changes made in future versions of 
   Beaker. Once the interfaces have been validated, they will be declared 
   "stable" and no further backwards-incompatible changes will be made to them.

HTTP resources
--------------

The lab controller exposes the following HTTP resources for use by the harness.

.. http:get:: /recipes/(recipe_id)/

   Returns recipe details. Response is in Beaker job results XML format, with 
   :mimetype:`application/xml` content type.
