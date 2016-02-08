-- Query for all CEE systems in Beaker that are reserved
SELECT system.fqdn, tg_user.user_name, reservation.start_time
FROM system
INNER JOIN reservation ON system.id = reservation.system_id
INNER JOIN tg_user ON reservation.user_id = tg_user.user_id
WHERE system.fqdn LIKE '%gsslab%' AND system.status != 'Removed' AND COALESCE(reservation.finish_time, '') = ''
ORDER BY system.fqdn ASC
