
-- Total duration of each user's recipes in hours ("machine-hours" used) for 
-- each month, broken down by arch.
-- Note: does not include manually reserved systems!

SELECT
    EXTRACT(YEAR_MONTH FROM recipe.start_time) AS `year_month`,
    job_owner.user_name AS username,
    distro_tree_arch.arch AS arch,
    SUM(TIMESTAMPDIFF(SECOND, recipe.start_time, COALESCE(recipe.finish_time, UTC_TIMESTAMP()))) / 60 / 60 AS machine_hours
FROM recipe
INNER JOIN machine_recipe ON recipe.id = machine_recipe.id
INNER JOIN recipe_set ON recipe.recipe_set_id = recipe_set.id
INNER JOIN job ON recipe_set.job_id = job.id
INNER JOIN tg_user job_owner ON job.owner_id = job_owner.user_id
INNER JOIN distro_tree ON recipe.distro_tree_id = distro_tree.id
INNER JOIN arch distro_tree_arch ON distro_tree.arch_id = distro_tree_arch.id
WHERE recipe.start_time IS NOT NULL
GROUP BY
    EXTRACT(YEAR_MONTH FROM recipe.finish_time),
    job_owner.user_id,
    distro_tree.arch_id
ORDER BY
    EXTRACT(YEAR_MONTH FROM recipe.finish_time),
    job_owner.user_id,
    distro_tree.arch_id;
