medusa

This is a TurboGears (http://www.turbogears.org) project. It can be
started by running the start-medusa.py script.


***Group ACL's***

User A       User B       User C
  Groups       Groups       Groups
  ------       -------      -------
               Group C      Group D

Group D                Group C
 Users   Systems        Users   Systems
-------  ---------     ------- --------
User C   System Z      User B   System X


System X         System Y          System Z
 Owner: UserA     Owner: UserB      Owner: UserB
 User:            User:             User:
 Shared: X        Shared:           Shared: X
 Private:         Private:          Private: X
 Groups           Groups            Groups
 ------           ------            ------
  Group C                            Group D


User A can see systems X and Y.
User B can see Systems X, Y and Z.
User C can see Systems X, Y and Z.

User A can become a user of System X.
User B can become a user of Systems X, Y and Z.
User C can become a user of System Z.

User A can modify System X settings.
User B can modify Systems Y and Z.
User C can not modify any System.

User A can give ownership of System X to someone else.
User B can give ownership of System Y and Z to someone else.
User C can not give ownership of any System.


An owner that is not sharing his system still needs to become the current user
of the system so that we can keep track of whats available to use.  Otherwise
we can't tell if a system is already being used.  We need to track not only 
what systems a user has access to but what systems are available.


*** History Audit ***

System_id, Service_id, Action, User_id, Date/Time

Service = Groups, Users, Owner, Notes, Power, Console, Details, Key/Value,
          Families
Action(s) = Add, Remove, Change

2, 1, Added to Group Intel, 3, 2008-09-23 15:27:50

1 = Groups
