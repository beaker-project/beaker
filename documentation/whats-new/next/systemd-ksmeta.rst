``systemd`` kickstart metadata variable is no longer set
========================================================

The undocumented ``systemd`` kickstart metadata variable is no longer populated 
by Beaker. If you have custom kickstart templates or snippets using this 
variable, update them to check if ``has_systemd`` is defined.

::

    {% if has_systemd is defined %}
    systemctl ...
    {% endif %}

This new variable is now documented, along with several other new variables 
which can be used in template conditionals to check for distro features.
See :ref:`kickstart-metadata`.
