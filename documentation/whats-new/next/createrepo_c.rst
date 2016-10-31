createrepo_c is the default
===========================

Beaker now uses the :program:`createrepo_c` tool by default when generating Yum 
repositories, since it is faster and more memory-efficient. It is still 
possible for Beaker administrators to switch back to the original 
:program:`createrepo` implementation by setting ``beaker.createrepo_command`` 
in the server configuration file.

(Contributed by Dan Callaghan in :issue:`1347156`.)
