-- Query for all CEE systems in Beaker that are loaned and get the loan date
SELECT w.fqdn1 AS fqdn, activity.created AS loan_date, activity.new_value AS loaned_to, system.loan_comment AS loan_comment
FROM (
    SELECT system.fqdn AS fqdn1, MAX(activity.id) AS id1
    FROM system
    INNER JOIN system_activity ON system_activity.system_id = system.id
    INNER JOIN activity ON activity.id = system_activity.id
    WHERE system.loan_id != 0
        AND system.fqdn LIKE '%gsslab%'
        AND activity.field_name = 'Loaned To'
        AND system.status != 'Removed'
    GROUP BY system.fqdn
    ORDER BY system.fqdn ASC
) w
INNER JOIN activity ON activity.id = w.id1
INNER JOIN system ON system.fqdn = w.fqdn1
