
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

_NAMESPACES = {}


def register(namespace):
    def decorate(cls):
        _NAMESPACES[namespace] = cls()
        return cls
    return decorate


def expose(func):
    func.exposed = True
    return func
