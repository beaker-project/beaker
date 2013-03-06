New client option, ``--hub``
============================

The ``bkr`` client now accepts a ``--hub`` option (for all subcommands), to 
override the hub URL specified in the configuration file. This can be used to 
submit jobs against a testing Beaker instance, for example.

If you maintain any third-party Beaker client subcommands or workflows, you 
should update them to pass all keyword arguments to the ``set_hub`` method, so 
that the ``--hub`` option is obeyed::

    def run(self, *args, **kwargs):
        self.set_hub(**kwargs)
        ...
