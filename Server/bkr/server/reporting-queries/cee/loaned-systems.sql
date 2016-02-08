-- Query for all CEE systems in Beaker that are loaned
SELECT system.fqdn, tg_user.user_name, system.loan_comment
FROM system
INNER JOIN tg_user ON system.loan_id = tg_user.user_id
WHERE system.fqdn LIKE '%gsslab%' AND system.status != 'Removed'
ORDER BY system.fqdn ASC
