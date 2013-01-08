-- Returns the mean avg(), min(), max() resource wait times.
-- The wait time is the time between the recipe_set queue time and
-- the recipe start time.

(SELECT 'All oVirt' AS fqdn,
        SEC_TO_TIME(AVG(TIME_TO_SEC(y.time_diff))) AS avg_wait_time,
        MIN(y.time_diff) AS min_wait_time,
        MAX(y.time_diff) AS max_wait_time FROM
    (SELECT  TIMEDIFF(recipe.start_time, recipe_set.queue_time) AS time_diff
     FROM recipe
        INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
        INNER JOIN recipe_resource AS rr ON rr.recipe_id = recipe.id
        INNER JOIN virt_resource AS vr ON rr.id = vr.id
    WHERE recipe.start_time IS NOT NULL) AS y)

UNION

(SELECT y.fqdn,
        SEC_TO_TIME(AVG(TIME_TO_SEC(y.time_diff))) AS avg_wait_time,
        MIN(y.time_diff) AS min_wait_time,
        MAX(y.time_diff) AS max_wait_time FROM
    (SELECT rr.fqdn AS fqdn,
    TIMEDIFF(recipe.start_time, recipe_set.queue_time) AS time_diff
    FROM recipe
        INNER JOIN recipe_set ON recipe_set.id = recipe.recipe_set_id
        INNER JOIN recipe_resource AS rr ON rr.recipe_id = recipe.id
        INNER JOIN system_resource AS sr ON rr.id = sr.id
    WHERE recipe.start_time IS NOT NULL) AS y GROUP BY y.fqdn)

ORDER BY avg_wait_time desc;

