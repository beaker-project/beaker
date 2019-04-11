
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
bkr job-comment: Add a comment to a job
=======================================

.. program:: bkr job-comment

Synopsis
--------

| :program:`bkr job-comment` [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to add the comment on.

The <taskspec> arguments follow the same format as in other :program:`bkr`
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>`
in :manpage:`bkr(1)`.

Only recipe sets, recipe tasks and task results can be commented on.

Options
-------

.. option:: --message

   Comment to be added to the job.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Add comment to recipe set 1234::

    bkr job-comment --message="Provisioning failed because boot order was
    wrong." RS:1234

See also
--------

:manpage:`bkr(1)`
"""

from bkr.client import BeakerCommand


class Job_Comment(BeakerCommand):
    """
    Comment on RecipeSet/RecipeTask/RecipeTaskResult
    """
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." \
            % self.normalized_name
        self.parser.add_option(
            "--message",
            default=None,
            help="Add comment to the given taskspec",
        )

    def run(self, *args, **kwargs):
        if len(args) < 1:
            self.parser.error('Please specify at least one taskspec to '
                              'comment on')

        msg = kwargs.pop("message", None)

        self.check_taskspec_args(args, permitted_types=['RS', 'T', 'TR'])

        message_data = {'comment': msg}
        if not message_data.get('comment'):
            self.parser.error('Comment text cannot be empty')

        self.set_hub(**kwargs)
        requests_session = self.requests_session()
        for task in args:
            task_type, task_id = task.split(":")
            if task_type.upper() == 'RS':
                url = 'recipesets/%s/comments/' % task_id
                res = requests_session.post(url, json=message_data)
                res.raise_for_status()

            elif task_type.upper() == 'T':
                url = 'recipes/%s/tasks/%s/comments/' % ('_', task_id)
                res = requests_session.post(url, json=message_data)
                res.raise_for_status()

            elif task_type.upper() == 'TR':
                result_id = task_id
                url = 'recipes/%s/tasks/%s/results/%s/comments/' \
                      % ('_', '_', result_id)
                res = requests_session.post(url, json=message_data)
                res.raise_for_status()
