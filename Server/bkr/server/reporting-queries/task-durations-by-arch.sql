
-- Min/mean/max of each task's execution duration in hours for the last month, 
-- broken down by arch.

SELECT
    task,
    arch,
    COUNT(recipe_task_id) AS executions,
    MIN(duration) AS min_duration,
    AVG(duration) AS avg_duration,
    MAX(duration) AS max_duration
FROM
    (SELECT
        task.name AS task,
        distro_tree_arch.arch AS arch,
        recipe_task.id AS recipe_task_id,
        TIMESTAMPDIFF(SECOND,
            CASE WHEN recipe_task.start_time < '2012-10-01 00:00:00'
                THEN '2012-10-01 00:00:00'
                ELSE recipe_task.start_time END,
            CASE WHEN recipe_task.finish_time IS NULL
                OR recipe_task.finish_time > '2012-11-01 00:00:00'
                THEN '2012-11-01 00:00:00'
                ELSE recipe_task.finish_time END) / 60 / 60 AS duration
    FROM recipe_task
    INNER JOIN task ON recipe_task.task_id = task.id
    INNER JOIN recipe ON recipe_task.recipe_id = recipe.id
    INNER JOIN distro_tree ON recipe.distro_tree_id = distro_tree.id
    INNER JOIN arch distro_tree_arch ON distro_tree.arch_id = distro_tree_arch.id
    WHERE recipe_task.start_time < '2012-11-01 00:00:00'
        AND (recipe_task.finish_time >= '2012-10-01 00:00:00'
             OR recipe_task.finish_time IS NULL)) x
GROUP BY task, arch
ORDER BY task, arch;
