Workflow commands accept --reserve
==================================

A new option :option:`--reserve <bkr --reserve>` is now accepted by 
:program:`bkr` workflow commands. This option adds the ``<reservesys/>`` 
element to each recipe in the job, causing Beaker to reserve the system after 
all tasks have finished executing (or if the recipe is aborted). The duration 
can be controlled using :option:`--reserve-duration <bkr --reserve-duration>`.
