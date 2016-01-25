-- Query for all non-CEE systems that have been provisioned...NOTE: limit to those that have been provisioned at least 20 times
SELECT q1.fqdn, q1.count
FROM (
    SELECT system.fqdn, COUNT(system.fqdn) AS count
    FROM system
    INNER JOIN system_activity ON system_activity.system_id = system.id
    INNER JOIN activity ON activity.id = system_activity.id
    INNER JOIN tg_user ON tg_user.user_id = activity.user_id
    INNER JOIN user_group ON user_group.user_id = tg_user.user_id
    INNER JOIN tg_group ON tg_group.group_id = user_group.group_id
    WHERE activity.action = 'Provision'
        AND tg_group.group_name = 'cee-users'
        AND system.fqdn NOT LIKE '%gsslab%'
    GROUP BY system.fqdn
    ORDER BY count DESC
) q1
WHERE q1.count >= 20
