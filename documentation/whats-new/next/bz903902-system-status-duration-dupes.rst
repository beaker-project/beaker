Delete duplicate system_status_duration rows with NULL finish_time (bug :issue:`903902`)
========================================================================================

Run the following SQL::

    DELETE FROM system_status_duration
    USING system_status_duration
    LEFT JOIN (
        SELECT system_id, MAX(start_time) start_time
        FROM system_status_duration 
        GROUP BY system_id) x
        ON system_status_duration.system_id = x.system_id
            AND system_status_duration.start_time = x.start_time
    WHERE finish_time IS NULL 
        AND x.start_time IS NULL;
