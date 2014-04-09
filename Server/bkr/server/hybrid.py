
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
A very simple, cut-down backport of the SQLAlchemy hybrid extension. Delete 
this when Beaker is on SQLAlchemy 0.7 or newer.
"""

class hybrid_method(object):

    def __init__(self, func):
        self.func = func
        self.expr = func

    def expression(self, func):
        self.expr = func
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self.expr.__get__(owner, owner.__class__)
        else:
            return self.func.__get__(instance, owner)

class hybrid_property(object):

    def __init__(self, fget):
        self.fget = fget
        self.expr = fget

    def expression(self, func):
        self.expr = func
        return self

    def __get__(self, instance, owner):
        if instance is None:
            return self.expr(owner)
        else:
            return self.fget(instance)
