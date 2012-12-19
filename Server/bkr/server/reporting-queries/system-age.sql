
-- Number of days each system has been in Beaker, and number of recipes 
-- executed.

SELECT
    system.fqdn AS fqdn,
    TIMESTAMPDIFF(DAY, system.date_added, UTC_TIMESTAMP()) AS age_days,
    COUNT(system_resource.id) AS recipe_count
FROM system
LEFT OUTER JOIN system_resource ON system_resource.system_id = system.id
WHERE system.status != 'Removed'
GROUP BY system.id
ORDER BY age_days DESC;
