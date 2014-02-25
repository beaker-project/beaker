Add power quiescent period
==========================

The quiescient period is a time period within which no power commands can be
run for a given system. It is measured in seconds, and is set per system on the
:ref:`Power Config <power-config>` page. The default value is 5.

The following changes are needed to be made to the schema.

    ALTER TABLE command_queue ADD COLUMN (quiescent_period int default NULL);
    ALTER TABLE power ADD COLUMN (power_quiescent_period int NOT NULL);

To rollback:

   ALTER TABLE command_queue DROP quiescent_period;
   ALTER TABLE power DROP power_quiescent_period;

