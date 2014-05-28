
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""
Custom exceptions for Beaker
"""

from bkr.common.bexceptions import BeakerException, BX

class NoChangeException(BeakerException):
    """This is raised when we want to signal we are doing a NOP"""
    pass

class StaleTaskStatusException(ValueError):
    """
    Raised when attempting to update the status of a task which was changed 
    concurrently by another transaction.
    """
    pass

class StaleCommandStatusException(ValueError):
    """
    Raised when attempting to update the status of a command which was changed 
    concurrently by another transaction.
    """
    pass

class StaleSystemUserException(BX):
    """
    Raised when attempting to update the user of a system, whilst
    the system user has already changed from what was expected.

    """
    pass


class InsufficientSystemPermissions(BX):
    """
    Raised when systems permissions available to a
    user are not sufficient.

    """
    pass

class DatabaseLookupError(LookupError):
    """
    Raised when attempting to look up a database entity
    which does not exist
    """
    pass
