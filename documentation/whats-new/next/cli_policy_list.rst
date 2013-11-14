Command line support for listing access policy rules
----------------------------------------------------

A new subcommand, ``policy-list`` has been added. Using this command
you can retrieve the current access policy rules for a system.

Example::

    $ bkr policy-list --system test1.example.com

    +----------------+--------+---------+-----------+
    |   Permission   |  User  |  Group  | Everybody |
    +----------------+--------+---------+-----------+
    | control_system |   X    | group12 |     No    |
    | control_system | user11 |    X    |     No    |
    |  edit_system   | user10 |    X    |     No    |
    +----------------+--------+---------+-----------+

(Contributed by Amit Saha in :issue:`1011378`)
