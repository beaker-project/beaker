
-- Number of times each system has been marked Broken and number of times 
-- a problem was reported against it.

SELECT
    system.fqdn AS fqdn,
    COALESCE(breakage_count, 0) breakage_count,
    COALESCE(problem_report_count, 0) problem_report_count
FROM system
LEFT OUTER JOIN (
    SELECT s1.id system_id, COUNT(system_status_duration.id) breakage_count
    FROM system s1
    INNER JOIN system_status_duration ON system_status_duration.system_id = s1.id
    AND system_status_duration.status = 'Broken'
    AND system_status_duration.start_time BETWEEN '2012-10-01 00:00:00' AND '2012-10-31 23:59:59'
    GROUP BY s1.id) x ON system.id = x.system_id
LEFT OUTER JOIN (
    SELECT s2.id system_id, COUNT(activity.id) problem_report_count
    FROM system s2
    INNER JOIN system_activity ON system_activity.system_id = s2.id
    INNER JOIN activity ON system_activity.id = activity.id
    AND activity.action = 'Reported problem'
    AND activity.created BETWEEN '2012-10-01 00:00:00' AND '2012-10-31 23:59:59'
    GROUP BY s2.id) y ON system.id = y.system_id;

-- This query can be rearranged to use scalar subqueries instead of joined 
-- subqueries. That will destroy performance on MySQL but gives much better 
-- performance in Teiid.
