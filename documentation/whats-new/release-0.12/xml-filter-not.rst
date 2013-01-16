``<not/>`` element in XML filters
=================================

The ``<not/>`` element can be used in ``<hostRequires/>`` and 
``<distroRequires/>`` to negate the meaning of any filter criteria it encloses. 
If it contains multiple filters, they are implicitly AND-ed together.

For example, the following filter matches systems which have a disk whose 
sector size is greater than 512 bytes (even if the same system also has a disk 
whose sector size is *not* greater than 512 bytes)::

    <disk>
        <sector_size op="&gt;" value="512" />
    </disk>

whereas the following filter matches systems which have *no* disks whose sector 
size is 512 bytes::

    <not>
        <disk>
            <sector_size op="=" value="512" />
        </disk>
    </not>
