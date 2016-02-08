-- Query for all CEE systems in Beaker and total up the number of times they have been provisioned
SELECT system.fqdn, COUNT(system.fqdn) AS count
FROM system
INNER JOIN system_activity ON system_activity.system_id = system.id
INNER JOIN activity ON activity.id = system_activity.id
WHERE activity.action = 'Provision'
    AND system.fqdn LIKE '%gsslab%'
GROUP BY system.fqdn
ORDER BY system.fqdn ASC
