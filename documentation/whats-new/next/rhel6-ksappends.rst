Changes to ks_appends semantics for Red Hat Enterprise Linux 6
==============================================================

Previously, for Red Hat Enterprise Linux 6, the ``packages``, ``pre`` and ``post``
sections in the kickstart were not terminated with an ``%end``. Hence,
additional kickstart commands specified using ``ks_appends`` weren't
parsed as commands by the kickstart parser. This has now been
rectified and hence allows you to specify one or more additional
kickstart commands using ``ks_appends``.

A consequence of this change is that if you want to specify a post
install scriptlet using ``ks_appends``, you will now have to begin a
new ``post`` section. For example::

    <ks_append>
    %post
    echo 'Custom script begin here'
    %end
    </ks_append>

Related bug: :issue:`907636`
