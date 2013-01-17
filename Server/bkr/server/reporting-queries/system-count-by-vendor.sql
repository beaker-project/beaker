
-- Number of systems by vendor.

SELECT
    system.vendor AS vendor,
    COUNT(system.id) AS system_count
FROM system
WHERE system.status != 'Removed'
GROUP BY
    system.vendor
ORDER BY
    system.vendor;
