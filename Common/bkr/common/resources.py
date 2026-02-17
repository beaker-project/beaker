# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import sys

if sys.version_info >= (3, 9):
    import importlib.resources
    import importlib.metadata

    def resource_stream(package, resource_name):
        return importlib.resources.files(package).joinpath(resource_name).open("rb")

    def resource_string(package, resource_name):
        return importlib.resources.files(package).joinpath(resource_name).read_bytes()

    def resource_listdir(package, resource_name):
        return [
            item.name
            for item in importlib.resources.files(package)
            .joinpath(resource_name)
            .iterdir()
        ]

    def resource_exists(package, resource_name):
        traversable = importlib.resources.files(package).joinpath(resource_name)
        return traversable.is_file() or traversable.is_dir()

    if sys.version_info >= (3, 10):
        def iter_entry_points(group):
            return importlib.metadata.entry_points(group=group)
    else:
        def iter_entry_points(group):
            return importlib.metadata.entry_points().get(group, [])

else:
    from pkg_resources import (
        resource_stream,
        resource_string,
        resource_listdir,
        resource_exists,
        iter_entry_points,
    )
