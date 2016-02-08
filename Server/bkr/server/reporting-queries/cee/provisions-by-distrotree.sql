-- Query for all CEE systems in Beaker and total up the number of times they have been provisioned with a particular operating system
SELECT activity.new_value AS operatingsystem, COUNT(activity.new_value) AS count
FROM activity
INNER JOIN system_activity ON system_activity.id = activity.id
INNER JOIN system ON system.id = system_activity.system_id
WHERE activity.action = 'Provision'
    AND system.fqdn LIKE '%gsslab%'
    AND system.status != 'Removed'
GROUP BY activity.new_value
ORDER BY count DESC
