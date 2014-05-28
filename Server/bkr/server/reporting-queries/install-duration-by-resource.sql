-- Returns the mean avg(), min() and max() resource installation durations
-- of each unique resource fqdn.
-- Guests and Virt are calculated on the total, as they are dynamic entities.

(SELECT
    rr.fqdn AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN system_resource AS sr ON rr.id = sr.id
GROUP BY system_id)

UNION

(SELECT
    'All Guest' AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN guest_resource AS gr ON gr.id = rr.id)

UNION

(SELECT
    'All OpenStack' AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, rr.install_started, rr.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN virt_resource AS vr ON vr.id = rr.id)

ORDER BY min_install_hours desc;

