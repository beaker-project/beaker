Support for caching images dropped
----------------------------------

The support for caching of netboot images on the lab controller has
been dropped. Hence, the images will be fetched from the distro tree
location every time the distro is provisioned.

It is worth pointing out that even with the earlier support for
caching, it was disabled by default.

(Contributed by Amit Saha in :issue:`968804`)
