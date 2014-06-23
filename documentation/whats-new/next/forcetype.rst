Force all log files named :file:`*.log` to ``text/plain``
=========================================================

The Apache configuration for serving Beaker log files now sets the MIME type 
for all files with :file:`*.log` extension to ``text/plain``.

In :file:`/etc/httpd/conf.d/beaker-lab-controller.conf` replace the section::

    <Files "console.log">
        ForceType text/plain
    </Files>

with::

    <Files "*.log">
        ForceType text/plain
    </Files>

If you are using an archive server for log storage, you should also make the 
corresponding change to its configuration.
