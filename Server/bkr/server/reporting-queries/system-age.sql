
-- Number of days each system has been in Beaker, and number of recipes 
-- executed.

SELECT
    system.fqdn AS fqdn,
    (SELECT TIMESTAMPDIFF(DAY, system.date_added, UTC_TIMESTAMP())
    FROM system s1
    WHERE s1.id = system.id) AS age_days,
    (SELECT COUNT(system_resource.id)
    FROM system_resource
    WHERE system_resource.system_id = system.id) AS recipe_count
FROM system
WHERE system.status != 'Removed'
ORDER BY age_days DESC;
