-- Query for all CEE systems in Beaker
SELECT fqdn, serial, status, location, vendor, model, lender
FROM system
WHERE fqdn LIKE '%gsslab%' AND system.status != 'Removed'
ORDER BY fqdn ASC
