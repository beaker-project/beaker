Workflow commands: Ignore other host selection criteria when machine specified
==============================================================================

If ``--machine`` and any other host selection criteria (via
``hostrequire``, ``systype``, ``random`` or ``keyvalue``) both are
specified, the latter will be ignored by the workflow commands.

An warning message will be emitted to the standard error.

(Contributed by Amit Saha in :issue:`1095026`.)
