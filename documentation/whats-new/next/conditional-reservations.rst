Conditional reservations
========================

You can now conditionally reserve the system at the end of your recipe when 
using the ``<reservesys/>`` element. A new attribute ``when=""`` is now 
supported, with the following values:

``onabort``
  The system will be reserved if the recipe status is Aborted.
``onfail``
  The system will be reserved if the recipe status is Aborted, or the result is 
  Fail.
``onwarn``
  The system will be reserved if the recipe status is Aborted, or the result is 
  Fail or Warn. This corresponds to the existing ``RESERVE_IF_FAIL=1`` option 
  for the ``/distribution/reservesys`` task.
``always``
  The system will be reserved unconditionally.

If the ``<reservesys/>`` element is given without a ``when=""`` attribute, it 
defaults to ``when="always"``, matching the behaviour from previous Beaker 
versions.

(Contributed by Dan Callaghan in :issue:`1100593`.)
