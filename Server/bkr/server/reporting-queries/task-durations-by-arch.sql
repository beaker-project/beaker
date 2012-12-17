
-- Min/mean/max of each task's execution duration in hours for the last month, 
-- broken down by arch.

SELECT
    task.name AS task,
    distro_tree_arch.arch AS arch,
    COUNT(recipe_task.id) AS executions,
    MIN(TIMESTAMPDIFF(SECOND, recipe_task.start_time, COALESCE(recipe_task.finish_time, UTC_TIMESTAMP()))) / 60 / 60 AS min_duration,
    AVG(TIMESTAMPDIFF(SECOND, recipe_task.start_time, COALESCE(recipe_task.finish_time, UTC_TIMESTAMP()))) / 60 / 60 AS avg_duration,
    MAX(TIMESTAMPDIFF(SECOND, recipe_task.start_time, COALESCE(recipe_task.finish_time, UTC_TIMESTAMP()))) / 60 / 60 AS max_duration
FROM recipe_task
INNER JOIN task ON recipe_task.task_id = task.id
INNER JOIN recipe ON recipe_task.recipe_id = recipe.id
INNER JOIN distro_tree ON recipe.distro_tree_id = distro_tree.id
INNER JOIN arch distro_tree_arch ON distro_tree.arch_id = distro_tree_arch.id
WHERE recipe_task.start_time IS NOT NULL
    AND recipe_task.start_time BETWEEN '2012-10-01 00:00:00' AND '2012-10-31 23:59:59'
GROUP BY
    EXTRACT(YEAR_MONTH FROM recipe.finish_time),
    task.id,
    distro_tree.arch_id
ORDER BY
    EXTRACT(YEAR_MONTH FROM recipe.finish_time),
    task.id,
    distro_tree.arch_id;
