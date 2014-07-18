-- Returns the system and its utilization percentage in
-- a duration

SELECT fqdn,
       SUM(TIMESTAMPDIFF(SECOND,
       CASE WHEN reservation.start_time < '2002-06-01 00:00:00' THEN '2002-06-01 00:00:00'
       ELSE reservation.start_time
       END,
       CASE WHEN reservation.finish_time IS NULL
       OR reservation.finish_time > '2002-07-01 00:00:00' THEN '2002-07-01 00:00:00'
       ELSE reservation.finish_time
       END))
       / TIMESTAMPDIFF(SECOND,
       '2002-06-01 00:00:00',
       '2002-07-01 00:00:00')
FROM reservation
       INNER JOIN system
       ON reservation.system_id = system.id
WHERE reservation.start_time <= '2002-07-01 00:00:00' AND
       ( reservation.finish_time > '2002-06-01 00:00:00' OR reservation.finish_time IS NULL )
GROUP BY system.fqdn;
