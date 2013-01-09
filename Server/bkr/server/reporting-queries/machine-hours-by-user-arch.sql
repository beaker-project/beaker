
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

-- This version of the query is limited to systems which are shared with no 
-- group restrictions (the "public pool"). See below if you want to remove or 
-- alter this filter.

SELECT
    tg_user.user_name AS username,
    system_arch.arch AS arch,
    SUM(TIMESTAMPDIFF(SECOND,
            GREATEST(reservation.start_time, '2012-10-01 00:00:00'),
            LEAST(COALESCE(reservation.finish_time, UTC_TIMESTAMP()),
                '2012-11-01 00:00:00')))
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
WHERE reservation.start_time < '2012-11-01 00:00:00'
    AND (reservation.finish_time >= '2012-10-01 00:00:00'
         OR reservation.finish_time IS NULL)
    -- limit to shared systems with no group restrictions
    AND system.private = 0 AND system.shared = 1
        AND NOT EXISTS (SELECT 1 FROM system_group WHERE system_id = system.id)
GROUP BY username, arch
ORDER BY username, arch;
