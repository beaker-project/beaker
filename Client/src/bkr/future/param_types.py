# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

from typing import List

import click

from bkr.future.taskspec import TaskSpec, TaskSpecError, TaskSpecType


class TaskSpecParamType(click.ParamType):
    name = "text"

    def __init__(self, permitted_specs: List[TaskSpecType] = None):
        self.permitted_specs: List[TaskSpecType] = permitted_specs or [
            key for key in TaskSpecType
        ]

    def convert(self, value: str, param: click.Argument, ctx: click.Context):
        value = super(TaskSpecParamType, self).convert(value, param, ctx)
        try:
            task_spec: TaskSpec = TaskSpec.from_string(value)
            if not self.is_permitted(task_spec):
                raise TaskSpecError(
                    f"TaskSpec {task_spec.type} is not allowed for {param.name} "
                    f"{str(param.__class__.__name__).lower()}."
                )
        except TaskSpecError as e:
            self.fail(e, param, ctx)
        return task_spec

    def is_permitted(self, task_spec: TaskSpec):
        return task_spec.type.name in [key.name for key in self.permitted_specs]


# Export default instance
TASKSPEC = TaskSpecParamType()
