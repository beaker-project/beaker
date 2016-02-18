-- Returns the mean avg(), min() and max() resource installation durations
-- of each unique resource fqdn.
-- Guests and Virt are calculated on the total, as they are dynamic entities.

(SELECT
    rr.fqdn AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN system_resource AS sr ON rr.id = sr.id
    INNER JOIN recipe ON rr.recipe_id = recipe.id
    INNER JOIN installation ON installation.recipe_id = recipe.id
GROUP BY rr.fqdn)

UNION

(SELECT
    'All Guest' AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN guest_resource AS gr ON gr.id = rr.id
    INNER JOIN recipe ON rr.recipe_id = recipe.id
    INNER JOIN installation ON installation.recipe_id = recipe.id)

UNION

(SELECT
    'All OpenStack' AS fqdn,
    AVG(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS avg_install_hours,
    MIN(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS min_install_hours,
    MAX(TIMESTAMPDIFF(SECOND, installation.install_started, installation.install_finished)) / 60 / 60 AS max_install_hours
FROM
    recipe_resource AS rr
    INNER JOIN virt_resource AS vr ON vr.id = rr.id
    INNER JOIN recipe ON rr.recipe_id = recipe.id
    INNER JOIN installation ON installation.recipe_id = recipe.id)

ORDER BY min_install_hours desc;

