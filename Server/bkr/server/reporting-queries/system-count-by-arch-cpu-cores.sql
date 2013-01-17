
-- Number of systems by arch and number of CPU cores.
-- Note that systems will be counted more than once if they support multiple 
-- arches (e.g. i386 and x86_64).

SELECT
    arch.arch AS arch,
    cpu.cores AS cpu_cores,
    COUNT(system.id) AS system_count
FROM system
INNER JOIN system_arch_map ON system_arch_map.system_id = system.id
INNER JOIN arch ON system_arch_map.arch_id = arch.id
LEFT OUTER JOIN cpu ON cpu.system_id = system.id
WHERE system.status != 'Removed'
GROUP BY arch.arch, cpu.cores
ORDER BY arch.arch, cpu.cores;
