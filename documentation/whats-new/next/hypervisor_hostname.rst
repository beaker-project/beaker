Access the hypervisor's hostname from a guest recipe (feature) (breakage)
-------------------------------------------------------------------------

The hypervisor's hostname is now exposed to tasks running in a guest
recipe via the ``HYPERVISOR_HOSTNAME`` environment variable
(when using the default beah test harness).

When returned from the ``simple harness`` API via ``/recipes/<recipe_id>``, the
``guestrecipe`` element is now within a ``recipe`` element (instead of directly
in the ``recipeSet`` element). The ``recipe`` element will contain the value
of the guestrecipe's hypervisor hostname in the ``system`` attribute.

(Contributed by Raymond Mancy in :issue:`887760`.)
