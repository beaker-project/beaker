What's New in Beaker 29?
========================

After a long pause, Beaker 29 is here, focusing on maintenance and ensuring the continuity and stability of the Beaker Project.
This release doesn't introduce any groundbreaking features but ensures that Beaker remains reliable and secure for its users.

Custom Bootloaders in Custom Distributions
------------------------------------------

We are expanding capabilities for custom distribution support.
Now, you can specify the location of the installer's netboot image.
It can be either relative to a given distribution tree or absolute path.
Beaker fetches the netboot image and prepares it in the TFTP directory.
The netboot image is available at the standard location `bootloader/fqdn/image`.

(Contributed by `Bill Peck  <https://github.com/p3ck>`_ -
`GH#165 <https://github.com/beaker-project/beaker/issues/165>`_)

Bug fixes
---------

A number of bug fixes are also included in this release:

* | `GH#200 <https://github.com/beaker-project/beaker/issues/200>`_:
    `beaker-import` is working again with latest Python 2.7 security fixes.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#194 <https://github.com/beaker-project/beaker/issues/194>`_:
    Beaker Client no longer depends on deprecated `cgi` library.
  | (Contributed by `Matej Dujava <https://github.com/mdujava>`_)
* | `GH#188 <https://github.com/beaker-project/beaker/issues/188>`_:
    Beaker Client no longer depends on deprecated `ssl.wrap_socket` function.
  | (Contributed by `Michael Hofmann  <https://github.com/mh21>`_)
* | `GH#168 <https://github.com/beaker-project/beaker/issues/168>`_:
    Beaker Server now requires nodejs-less with version lower than 2.0
    to avoid issues with building assets.
  | (Contributed by `Martin Styk <https://github.com/StykMartin>`_)
* | `GH#177 <https://github.com/beaker-project/beaker/issues/177>`_:
    Fixed issue where JUnit result wasn't properly decoded in Beaker client.
  | (Contributed by `Bill Peck  <https://github.com/p3ck>`_)
