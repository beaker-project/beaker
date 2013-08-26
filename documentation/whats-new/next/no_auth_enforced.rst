No authentication configuration enforced in Kickstarts
------------------------------------------------------

Previously, Beaker configured system authentication to use MD5 hashes
on all distributions other than RHEL6. This configuration has now been
removed so that the default for every distribution is used instead.

Additionally, users may now specify a specific authentication configuration
using the ``ks_meta`` XML attribute in their recipe specification. For
example::

    <recipe ks_meta="auth='--enableshadow --enablemd5'">

(Contributed by Amit Saha in :issue:`989924`)
