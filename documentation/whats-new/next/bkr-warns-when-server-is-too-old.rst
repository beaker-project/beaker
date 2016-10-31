bkr warns when the server is too old
====================================

If the :program:`bkr` client is making a request to the server and it fails, 
the client will print an additional warning message if the server's major 
version is less than the client's. This is to help detect the case where the 
client is attempting to use a new API against an older server which does not 
support it.

(Contributed by Dan Callaghan in :issue:`1029287`.)
