"""
Blatently copied from cobbler.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

def uniquify(seq, idfun=None):
    # credit: http://www.peterbe.com/plog/uniqifiers-benchmark
    # FIXME: if this is actually slower than some other way, overhaul it
    if idfun is None:
        def idfun(x):
           return x
    seen = {}
    result = []
    for item in seq:
        marker = idfun(item)
        if marker in seen:
            continue
        seen[marker] = 1
        result.append(item)
    return result

def consolidate(node,results):
    """
    Merge data from a given node with the aggregate of all
    data from past scanned nodes.  Hashes and arrays are treated
    specially.
    """
    node_data =  node
    #node_data =  node.to_datastruct()

    # if the node has any data items labelled <<inherit>> we need to expunge them.
    # so that they do not override the supernodes.
    node_data_copy = {}
    for key in node_data:
       value = node_data[key]
       if value != "<<inherit>>":
          if type(value) == type({}):
              node_data_copy[key] = value.copy()
          elif type(value) == type([]):
              node_data_copy[key] = value[:]
          else:
              node_data_copy[key] = value

    for field in node_data_copy:

       data_item = node_data_copy[field]
       if results.has_key(field):

          # now merge data types seperately depending on whether they are hash, list,
          # or scalar.

          fielddata = results[field]

          if type(fielddata) == dict:
             # interweave hash results
             results[field].update(data_item)
          elif type(fielddata) == list or type(fielddata) == tuple:
             # add to lists (cobbler doesn't have many lists)
             # FIXME: should probably uniqueify list after doing this
             results[field].extend(data_item)
             results[field] = uniquify(results[field])
          else:
             # just override scalars
             results[field] = data_item
       else:
          results[field] = data_item

    # now if we have any "!foo" results in the list, delete corresponding
    # key entry "foo", and also the entry "!foo", allowing for removal
    # of kernel options set in a distro later in a profile, etc.

    hash_removals(results,"kernel_options")
    hash_removals(results,"kernel_options_post")
    hash_removals(results,"ks_meta")

def hash_removals(results,subkey):
    if not results.has_key(subkey):
        return
    scan = results[subkey].keys()
    for k in scan:
        if k.startswith("!") and k != "!":
           remove_me = k[1:]
           if results[subkey].has_key(remove_me):
               del results[subkey][remove_me]
           del results[subkey][k]

def hash_to_string(hash):
    """
    Convert a hash to a printable string.
    used primarily in the kernel options string
    and for some legacy stuff where koan expects strings
    (though this last part should be changed to hashes)
    """
    buffer = ""
    if type(hash) != dict:
       return hash
    for key in hash:
       value = hash[key]
       if value is None:
           buffer = buffer + str(key) + " "
       elif type(value) == list:
           # this value is an array, so we print out every
           # key=value
           for item in value:
              buffer = buffer + str(key) + "=" + str(item) + " "
       else:
          buffer = buffer + str(key) + "=" + str(value) + " "
    return buffer

def string_to_hash(options,delim=" ",allow_multiples=True):
    if options == "<<inherit>>":
        options = {}

    if options is None or options == "delete":
        return {}
    new_dict = {}
    tokens = options.split(delim)
    for t in tokens:
        tokens2 = t.split("=")
        if len(tokens2) == 1 and tokens2[0] != '':
            # this is a singleton option, no value
            tokens2.append(None)
        elif tokens2[0] == '':
            return {}

        # if we're allowing multiple values for the same key,
        # check to see if this token has already been
        # inserted into the dictionary of values already
        if tokens2[0] in new_dict.keys() and allow_multiples:
            # if so, check to see if there is already a list of values
            # otherwise convert the dictionary value to an array, and add
            # the new value to the end of the list
            if type(new_dict[tokens2[0]]) == list:
                new_dict[tokens2[0]].append(tokens2[1])
            else:
                new_dict[tokens2[0]] = [new_dict[tokens2[0]], tokens2[1]]
        else:
            new_dict[tokens2[0]] = tokens2[1]
    new_dict.pop('', None)
    return new_dict
