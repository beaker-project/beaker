-- Returns the mean avg(), min() and max() resource installation durations
-- of each unique resource fqdn.
-- Guests and Virt are calculated on the total, as they are dynamic entities.

(SELECT
    rr.fqdn AS fqdn,
    SEC_TO_TIME(AVG(TIME_TO_SEC(TIMEDIFF(rr.install_finished, rr.install_started)))) AS avg_install_time,
    MIN(TIMEDIFF(rr.install_finished, rr.install_started)) AS min_install_time,
    MAX(TIMEDIFF(rr.install_finished, rr.install_started)) AS max_install_time
FROM
    recipe_resource AS rr
    INNER JOIN system_resource AS sr ON rr.id = sr.id
GROUP BY system_id)

UNION

(SELECT
    'All Guest' AS fqdn,
    SEC_TO_TIME(AVG(TIME_TO_SEC(TIMEDIFF(rr.install_finished, rr.install_started)))) AS avg_install_time,
    MIN(TIMEDIFF(rr.install_finished,rr.install_started)) AS min_install_time,
    MAX(TIMEDIFF(rr.install_finished, rr.install_started)) AS max_install_time
FROM
    recipe_resource AS rr
    INNER JOIN guest_resource AS gr ON gr.id = rr.id)

UNION

(SELECT
    'All Virt' AS fqdn,
    SEC_TO_TIME(AVG(TIME_TO_SEC(TIMEDIFF(rr.install_finished, rr.install_started)))) AS avg_install_time,
    MIN(TIMEDIFF(rr.install_finished, rr.install_started)) AS min_install_time,
    MAX(TIMEDIFF(rr.install_finished, rr.install_started)) AS max_install_time
FROM
    recipe_resource AS rr
    INNER JOIN virt_resource AS vr ON vr.id = rr.id)

ORDER BY min_install_time desc;

