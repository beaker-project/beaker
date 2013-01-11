
-- Number of systems by arch and GB of memory.
-- Note that systems will be counted more than once if they support multiple 
-- arches (e.g. i386 and x86_64).

SELECT arch, memory_gb, COUNT(system_id)
FROM
    (SELECT
        arch.arch AS arch,
        ROUND(system.memory / 1024) AS memory_gb, -- memory is in MB
        system.id AS system_id
    FROM system
    INNER JOIN system_arch_map ON system_arch_map.system_id = system.id
    INNER JOIN arch ON system_arch_map.arch_id = arch.id
    WHERE system.status != 'Removed') x
GROUP BY arch, memory_gb
ORDER BY arch, memory_gb;
