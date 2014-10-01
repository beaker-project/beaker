Workflow commands no longer use ``STABLE``
==========================================

The :program:`bkr` workflow commands no longer filter for distros tagged 
``STABLE`` by default. If your Beaker installation is using the ``STABLE`` tag, 
you can apply the filter explicitly by adding ``--tag=STABLE`` when invoking 
workflow commands.
