-- Query for all CEE systems in Beaker and get the name of the last operating system installed
SELECT system.fqdn, activity.new_value AS operatingsystem
FROM system
INNER JOIN (
    SELECT system_activity.system_id AS my_system_id, MAX(activity.id) AS latestactivity_id
    FROM activity
    INNER JOIN system_activity ON system_activity.id = activity.id
    INNER JOIN system ON system.id = system_activity.system_id
    WHERE activity.action = 'Provision'
        AND system.fqdn LIKE '%gsslab%'
        AND system.status != 'Removed'
    GROUP BY system_activity.system_id
) my_table ON my_table.my_system_id = system.id
INNER JOIN activity ON activity.id = my_table.latestactivity_id
ORDER BY system.fqdn ASC
