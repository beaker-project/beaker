# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

from enum import Enum


class TaskSpecError(ValueError):
    pass


class TaskSpecType(Enum):
    J = "Job"
    RS = "RecipeSet"
    R = "Recipe"
    T = "RecipeTask"
    TR = "RecipeTaskResult"


class TaskSpec:
    def __init__(self, task_type: TaskSpecType, value: str) -> None:
        self.type: TaskSpecType = task_type
        self.value: str = value

    @classmethod
    def from_string(cls, task: str) -> "TaskSpec":
        if ":" not in task:
            raise TaskSpecError(f"Incorrect value for task: {task}.")

        spec_type, spec_id = task.split(":", 1)
        try:
            task_spec = cls(TaskSpecType[spec_type], spec_id)
        except KeyError:
            raise TaskSpecError(
                f"Type {spec_type} is not recognized as supported TaskSpec."
            )
        return task_spec

    def __str__(self) -> str:
        return f"{self.type.name}:{self.value}"
