-- Returns the mean avg(), min(), max() resource wait times.
-- The wait time is the time between the recipe_set queue time and
-- the recipe start time.

(SELECT 'All OpenStack' AS fqdn,
        AVG(y.time_diff) AS avg_wait_hours,
        MIN(y.time_diff) AS min_wait_hours,
        MAX(y.time_diff) AS max_wait_hours FROM
    (SELECT  TIMESTAMPDIFF(SECOND, recipe_set.queue_time, recipe.start_time) / 60 / 60 AS time_diff
     FROM recipe
        INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
        INNER JOIN recipe_resource AS rr ON rr.recipe_id = recipe.id
        INNER JOIN virt_resource AS vr ON rr.id = vr.id
    WHERE recipe.start_time IS NOT NULL) AS y)

UNION

(SELECT y.fqdn,
        AVG(y.time_diff) AS avg_wait_hours,
        MIN(y.time_diff) AS min_wait_hours,
        MAX(y.time_diff) AS max_wait_hours FROM
    (SELECT rr.fqdn AS fqdn,
    TIMESTAMPDIFF(SECOND, recipe_set.queue_time, recipe.start_time) / 60 / 60 AS time_diff
    FROM recipe
        INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
        INNER JOIN recipe_resource AS rr ON rr.recipe_id = recipe.id
        INNER JOIN system_resource AS sr ON rr.id = sr.id
    WHERE recipe.start_time IS NOT NULL) AS y GROUP BY y.fqdn)

ORDER BY avg_wait_hours desc;

