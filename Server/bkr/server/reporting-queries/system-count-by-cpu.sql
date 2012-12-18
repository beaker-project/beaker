
-- Number of systems by CPU type.

SELECT
    cpu.vendor AS cpu_vendor,
    cpu.model AS cpu_model,
    cpu.family AS cpu_family,
    cpu.stepping AS cpu_stepping,
    COUNT(system.id) AS system_count
FROM system
LEFT OUTER JOIN cpu ON cpu.system_id = system.id
WHERE system.status != 'Removed'
GROUP BY
    cpu.vendor,
    cpu.model,
    cpu.family,
    cpu.stepping
ORDER BY
    cpu.vendor,
    cpu.model,
    cpu.family,
    cpu.stepping;
