
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

def parse_content_type(value):
    """
    Return just content type, without options
    """
    groups = value.split(';', 1)
    return groups[0]
