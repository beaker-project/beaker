
-- Number of times each system has been marked Broken and number of times 
-- a problem was reported against it.

SELECT
    system.fqdn AS fqdn,
    COUNT(DISTINCT system_status_duration.id) AS breakage_count,
    COUNT(DISTINCT activity.id) AS problem_report_count
FROM system
LEFT OUTER JOIN system_status_duration ON system_status_duration.system_id = system.id
    AND system_status_duration.status = 'Broken'
    AND system_status_duration.start_time BETWEEN '2012-10-01 00:00:00' AND '2012-10-31 23:59:59'
LEFT OUTER JOIN system_activity ON system_activity.system_id = system.id
LEFT OUTER JOIN activity ON system_activity.id = activity.id
    AND activity.action = 'Reported problem'
    AND activity.created BETWEEN '2012-10-01 00:00:00' AND '2012-10-31 23:59:59'
GROUP BY system.id;
