Password hashes use a more secure, salted form
==============================================

Beaker account passwords are now stored in a more secure form, using PBKDF2 
with SHA512 HMAC and a unique random salt per user. Previously Beaker stored an 
unsalted SHA1 hash of each password. The password storage implementation is 
provided by the `passlib <http://pythonhosted.org/passlib/>`_ library.

(Contributed by Dan Callaghan in :issue:`994751`.)

Expand the ``password`` column
------------------------------

To accommodate the new password hashes, the ``tg_user.password`` column must be 
expanded. Run the following SQL::

    ALTER TABLE tg_user
        MODIFY password TEXT DEFAULT NULL;

To roll back, run the following SQL::

    ALTER TABLE tg_user
        MODIFY password VARCHAR(40) DEFAULT NULL;
