INSERT INTO lab_controller(id, fqdn, disabled, user_id)
VALUES(1, 'lab.controller', 0, 1);

INSERT INTO system (id, fqdn, date_added, owner_id, type,
    status, kernel_type_id, lab_controller_id)
VALUES (1, 'with.lab.controller', '2015-01-01 00:00:00', 1, 1, 1, 1, 1);


INSERT INTO system (id, fqdn, date_added, owner_id, type,
    status, kernel_type_id)
VALUES (2, 'without.lab.controller', '2015-01-01 00:00:00', 1, 1, 1, 1);


INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (1, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (2, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (3, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (4, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (5, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (6, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (7, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (8, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');
INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (9, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');

INSERT INTO command_queue (id, system_id, status)
VALUES (1, 1, 'Running');

INSERT INTO command_queue (id, system_id, status)
VALUES (2, 1, 'Queued');

INSERT INTO command_queue (id, system_id, status)
VALUES (3, 1, 'Queued');

INSERT INTO command_queue (id, system_id, status)
VALUES (4, 1, 'Queued');


INSERT INTO command_queue (id, system_id, status)
VALUES (5, 2, 'Running');

INSERT INTO command_queue (id, system_id, status)
VALUES (6, 2, 'Queued');

INSERT INTO command_queue (id, system_id, status)
VALUES (7, 2, 'Queued');

INSERT INTO command_queue (id, system_id, status)
VALUES (8, 2, 'Queued');

INSERT INTO command_queue (id, system_id, status)
VALUES (9, 2, 'Failed');

