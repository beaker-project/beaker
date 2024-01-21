# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import os

logger = logging.getLogger(__name__)


def get_console_files(console_logs_directory, system_name):
    """Return a list of the console log files for a system

    Given a path to the console_logs_directory and the FQDN (Fully Qualified
    Domain Name) of the system. Search the console_logs_directory and return a
    list containing tuples of the full path name to the log file and the name
    to use when uploading the logfile for log files that are for system_name.

    :param console_logs_directory: Path to the console logs directory
    :param system_name: Fully qualified domain name of the system
    :return: List[Tuple[absolute path to log file, name to use for log file]]
    """
    if not os.path.isdir(console_logs_directory):
        logger.info(
            "Console files directory does not exist: %s", console_logs_directory
        )
        return []

    if not system_name:
        logger.info("No System Name for console log file...Ignoring")
        return []

    output = []
    for filename in sorted(os.listdir(console_logs_directory)):
        if filename.startswith(system_name):
            full_path = os.path.join(console_logs_directory, filename)
            if filename == system_name:
                logfile_name = "console.log"
            else:
                description = filename[len(system_name):]
                # Remove leading hyphens
                description = description.lstrip("-")
                logfile_name = "console-{}.log".format(description)
            output.append((full_path, logfile_name))
    return output
