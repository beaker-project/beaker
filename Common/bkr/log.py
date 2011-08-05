# -*- coding: utf-8 -*-


import os
import logging
import logging.handlers
try:
    from cloghandler import ConcurrentRotatingFileHandler as RFHandler
except ImportError:
    # Next 2 lines are optional:  issue a warning to the user
    from warnings import warn
    warn("ConcurrentLogHandler package not installed.  Using builtin log handler")
    from logging.handlers import RotatingFileHandler as RFHandler




__all__ = (
    "BRIEF_LOG_FORMAT",
    "VERBOSE_LOG_FORMAT",
    "add_stderr_logger",
    "add_file_logger",
    "add_rotating_file_logger",
    "LoggingBase",
)


BRIEF_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] %(message)s"
VERBOSE_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] {%(process)5d} %(name)s:%(lineno)4d %(message)s"


###########
# Following hack enables 'VERBOSE' log level in the python logging module and Logger class.
# This means you need to import bkr.log before you can use 'VERBOSE' logging.


logging.VERBOSE = 15
logging.addLevelName(15, "VERBOSE")


def verbose(self, msg, *args, **kwargs):
    """
    Log 'msg % args' with severity 'VERBOSE'.

    To pass exception information, use the keyword argument exc_info with
    a true value, e.g.

    logger.info("Houston, we have a %s", "interesting problem", exc_info=1)
    """
    if self.manager.disable >= logging.VERBOSE:
        return
    if logging.VERBOSE >= self.getEffectiveLevel():
        self._log(*(logging.VERBOSE, msg, args), **kwargs)
logging.Logger.verbose = verbose


def verbose(msg, *args, **kwargs):
    """
    Log a message with severity 'VERBOSE' on the root logger.
    """
    if len(logging.root.handlers) == 0:
        logging.basicConfig()
    logging.root.verbose(*((msg, ) + args), **kwargs)
logging.verbose = verbose
del verbose


# end of hack
###########


def add_stderr_logger(logger, log_level=None, format=None):
    """Add a stderr logger to the logger."""
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)


def add_file_logger(logger, logfile, log_level=None, format=None, mode="a"):
    """Add a file logger to the logger."""
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    # touch the logfile
    if not os.path.exists(logfile):
        try:
            fo = open(logfile, "w")
            fo.close()
        except (ValueError, IOError):
            return

    # is the logfile really a file?
    if not os.path.isfile(logfile):
        return

    # check if the logfile is writable
    if not os.access(logfile, os.W_OK):
        return

    handler = logging.FileHandler(logfile, mode=mode)
    handler.setFormatter(logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)


def add_rotating_file_logger(logger, logfile, log_level=None, format=None, mode="a", maxBytes=10*(1024**2), backupCount=5):
    """Add a rotating file logger to the logger."""
    log_level = log_level or logging.DEBUG
    format = format or BRIEF_LOG_FORMAT

    # touch the logfile
    if not os.path.exists(logfile):
        try:
            fo = open(logfile, "w")
            fo.close()
        except (ValueError, IOError):
            return

    # is the logfile really a file?
    if not os.path.isfile(logfile):
        return

    # check if the logfile is writable
    if not os.access(logfile, os.W_OK):
        return

    handler = RFHandler(logfile, maxBytes=maxBytes, backupCount=backupCount, mode=mode)
    handler.setFormatter(logging.Formatter(format, datefmt="%Y-%m-%d %H:%M:%S"))
    handler.setLevel(log_level)
    logger.addHandler(handler)
