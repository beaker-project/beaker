
-- Total duration of each user's system reservations, both manual and through 
-- the scheduler ("machine-hours" used), broken down by arch.
-- Note that this does not include dynamically created virtual machines, 
-- because there are no system reservation rows for those.

-- Systems which support multiple architectures (for example, i386 and x86_64) 
-- are counted towards the arch with the lexographically largest name. 
-- Effectively for all known arches this means they are counted towards the 
-- 64-bit version of the architecture. This is achieved below with 
-- MAX(arch.arch) in a subquery.
-- Note that in cases where a 64-bit-capable system is provisioned with 
-- a 32-bit distro, this may lead to discrepancies with the recipe-hours 
-- report, which considers only the arch of the recipe distro.

-- This version of the query is limited to systems which are available 
-- to all users (the "public pool"). See below if you want to remove or 
-- alter this filter.

SELECT
    tg_user.user_name AS username,
    system_arch.arch AS arch,
    SUM(TIMESTAMPDIFF(SECOND,
            CASE WHEN reservation.start_time < '2012-10-01 00:00:00'
                THEN '2012-10-01 00:00:00'
                ELSE reservation.start_time END,
            CASE WHEN reservation.finish_time IS NULL
                OR reservation.finish_time > '2012-11-01 00:00:00'
                THEN '2012-11-01 00:00:00'
                ELSE reservation.finish_time END))
        / 60 / 60 AS machine_hours
FROM reservation
INNER JOIN system ON reservation.system_id = system.id
INNER JOIN
    (SELECT system.id, MAX(arch.arch) arch
    FROM system
    LEFT OUTER JOIN system_arch_map ON system_arch_map.system_id = system.id
    LEFT OUTER JOIN arch ON system_arch_map.arch_id = arch.id
    GROUP BY system.id) system_arch
    ON system_arch.id = system.id
INNER JOIN tg_user ON reservation.user_id = tg_user.user_id
LEFT OUTER JOIN system_access_policy ON system.active_access_policy_id = system_access_policy.id
WHERE reservation.start_time < '2012-11-01 00:00:00'
    AND (reservation.finish_time >= '2012-10-01 00:00:00'
         OR reservation.finish_time IS NULL)
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
GROUP BY tg_user.user_name, system_arch.arch
ORDER BY tg_user.user_name, system_arch.arch;
