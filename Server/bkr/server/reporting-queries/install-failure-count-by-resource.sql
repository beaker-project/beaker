-- Total number of install failures for each unique resource,
-- apart from Virt and Guest resources which are counted in their
-- totality as individually they are not a unique trackable entity.
-- For systems that have power configurations
-- (the majority), an install failure is defined as systems that rebooted but
-- did not finish installing. For systems that do not have their power
-- configured, instead of the 'rebooted' status we check
-- against 'install_started'.

(SELECT
   'All oVirt' AS fqdn,
    COUNT(vr.id) AS failed_recipes
FROM
    recipe_resource AS rr
    INNER JOIN recipe ON recipe.id = rr.recipe_id
    INNER JOIN virt_resource AS vr ON vr.id = rr.id
WHERE
    recipe.status NOT IN('Running', 'Cancelled')
    AND COALESCE(rr.rebooted, rr.install_started) IS NOT NULL
    AND rr.install_finished IS NULL)

UNION

(SELECT
    'All Guest' AS fqdn,
    COUNT(gr.id) as failed_recipes
FROM
    recipe_resource AS rr
    INNER JOIN recipe ON recipe.id = rr.recipe_id
    INNER JOIN guest_resource AS gr ON rr.id = gr.id
WHERE
    recipe.status NOT IN('Running', 'Cancelled')
    AND COALESCE(rr.rebooted, rr.install_started) IS NOT NULL
    AND rr.install_finished IS NULL)

UNION

(SELECT
    rr.fqdn AS fqdn,
    COUNT(rr1.id) AS failed_recipes
FROM
    recipe_resource AS rr
    LEFT OUTER JOIN recipe ON recipe.id = rr.recipe_id AND recipe.status NOT IN('Running', 'Cancelled')
    INNER JOIN system_resource AS sr ON sr.id = rr.id
    LEFT OUTER JOIN
        recipe_resource AS rr1 ON recipe.id = rr1.recipe_id
        AND COALESCE(rr1.rebooted, rr1.install_started) IS NOT NULL
        AND rr1.install_finished IS NULL
GROUP BY sr.system_id)

ORDER BY failed_recipes desc
