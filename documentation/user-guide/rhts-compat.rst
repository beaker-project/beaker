The ``rhts-compat`` service
===========================

On Red Hat Enterprise Linux 6 and earlier releases, tasks are executed by 
a special service called ``rhts-compat``. This service is last in the startup 
order and it intentionally "hangs" forever without fully starting up, so that 
tasks can be run attached to the console. As a consequence, when the 
``rhts-compat`` service is running it is not possible to log in to the system's 
console.

If you don't need this compatibility mode for your tasks, you can disable it in 
the :doc:`task metadata <task-metadata>` by adding::

    RhtsOptions: -Compatible

Or you can disable it in your Beaker job definition by adding a task 
parameter::

    <task ...>
      <params>
        <param name="RHTS_OPTION_COMPATIBLE" value=""/>
      </params>
    </task>

The service can also be disabled system-wide by setting an environment variable 
in :file:`/etc/profile.d/task-overrides-rhts.sh`, for example using a kickstart 
snippet::

    <ks_append>
    %post
    cat >>/etc/profile.d/task-overrides-rhts.sh <<EOF
    export RHTS_OPTION_COMPATIBLE=
    export RHTS_OPTION_COMPAT_SERVICE=
    EOF
    %end
    </ks_append>

On distros using systemd (which includes Red Hat Enterprise Linux 7 and all 
supported Fedora releases) the ``rhts-compat`` service cannot be used and is 
always unconditionally disabled.
