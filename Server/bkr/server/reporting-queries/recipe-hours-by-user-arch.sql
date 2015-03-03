
-- Total duration of each user's recipes in hours ("recipe-hours" used) broken 
-- down by the arch of the recipe distro. This query includes recipes which ran 
-- on dynamically created virtual machines. However it does not include guest 
-- recipes (VMs created on a host recipe) since they do not consume any 
-- independent resources.
-- Note that this does not include any manually reserved systems, since there 
-- is no associated recipe when a system is manually reserved. See the 
-- "machine-hours" query for that.

-- This version of the query is limited to systems which are available 
-- to all users (the "public pool"). See below if you want to remove or 
-- alter this filter.

SELECT
    job_owner.user_name AS username,
    distro_tree_arch.arch AS arch,
    SUM(TIMESTAMPDIFF(SECOND,
            CASE WHEN recipe.start_time < '2012-10-01 00:00:00'
                THEN '2012-10-01 00:00:00'
                ELSE recipe.start_time END,
            CASE WHEN recipe.finish_time IS NULL
                OR recipe.finish_time > '2012-11-01 00:00:00'
                THEN '2012-11-01 00:00:00'
                ELSE recipe.finish_time END))
        / 60 / 60 AS recipe_hours
FROM recipe
INNER JOIN machine_recipe ON recipe.id = machine_recipe.id
INNER JOIN recipe_set ON recipe.recipe_set_id = recipe_set.id
INNER JOIN job ON recipe_set.job_id = job.id
INNER JOIN tg_user job_owner ON job.owner_id = job_owner.user_id
INNER JOIN distro_tree ON recipe.distro_tree_id = distro_tree.id
INNER JOIN arch distro_tree_arch ON distro_tree.arch_id = distro_tree_arch.id
INNER JOIN recipe_resource ON recipe_resource.recipe_id = recipe.id
LEFT OUTER JOIN system_resource ON system_resource.id = recipe_resource.id
LEFT OUTER JOIN system ON system_resource.system_id = system.id
LEFT OUTER JOIN system_access_policy ON system.active_access_policy_id = system_access_policy.id
WHERE recipe.start_time < '2012-11-01 00:00:00'
    AND (recipe.finish_time >= '2012-10-01 00:00:00'
         OR recipe.finish_time IS NULL)
    -- limit to systems which everybody is allowed to view and reserve
    AND EXISTS (
        SELECT 1
        FROM system_access_policy_rule
        WHERE policy_id = system_access_policy.id
            AND permission = 'view'
            AND user_id IS NULL AND group_id IS NULL)
    AND EXISTS (
        SELECT 1
        FROM system_access_policy_rule
        WHERE policy_id = system_access_policy.id
            AND permission = 'reserve'
            AND user_id IS NULL AND group_id IS NULL)
GROUP BY job_owner.user_name, distro_tree_arch.arch
ORDER BY job_owner.user_name, distro_tree_arch.arch;
