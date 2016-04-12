INSERT INTO system (id, fqdn, date_added, owner_id, type,
    status, kernel_type_id)
VALUES (1, 'test.fqdn.name', '2015-01-01 00:00:00', 1, 1, 1, 1);

INSERT INTO osmajor (id, osmajor)
VALUES (1, 'osmajor');

INSERT INTO osversion (id, osmajor_id, osminor)
VALUES (1, 1, '0');

INSERT INTO distro (id, osversion_id, name, date_created)
VALUES (1, 1, 'distro', '2015-01-01 00:00:00');

INSERT INTO distro_tree (id, distro_id, arch_id, date_created)
VALUES (1, 1, 1, '2015-01-01 00:00:00');

INSERT INTO job (id, owner_id, retention_tag_id, dirty_version,
    clean_version, status)
VALUES (1, 1, 1, '', '', 'Completed');

INSERT INTO recipe_set (id, job_id, queue_time, status)
VALUES (1, 1, '2016-02-16 00:00:00', 'Completed');

-- Recipe 1 is a machine_recipe with a system_resource.

INSERT INTO rendered_kickstart (id, kickstart)
VALUES (1, 'lol');

INSERT INTO recipe (id, type, recipe_set_id, autopick_random, status,
    distro_tree_id, start_time, finish_time, rendered_kickstart_id)
VALUES (1, 'machine_recipe', 1, FALSE, 'Completed',
    1, '2016-02-16 01:00:10', '2016-02-16 02:00:00', 1);

INSERT INTO machine_recipe (id) VALUES (1);

INSERT INTO reservation (id, user_id, system_id, type, start_time, finish_time)
VALUES (1, 1, 1, 'recipe', '2016-02-16 01:00:00', '2016-02-16 02:00:00');

INSERT INTO recipe_resource (id, type, recipe_id, rebooted, install_started,
    install_finished, postinstall_finished)
VALUES (1, 'system', 1, '2016-02-16 01:00:05', '2016-02-16 01:01:00',
    '2016-02-16 01:20:00', '2016-02-16 01:21:00');

INSERT INTO system_resource (id, system_id, reservation_id) VALUES (1, 1, 1);

INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (1, 1, '2016-02-16 01:00:04', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');

INSERT INTO command_queue (id, updated, system_id, kernel_options, callback)
VALUES (1, '2016-02-16 01:00:04', 1, 'ks=lol', 'bkr.server.model.auto_cmd_handler');

-- Also include an extra configure_netboot command which was triggered 
-- manually by a user during the recipe (it should be ignored).

INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (2, 1, '2016-02-16 01:30:00', 'command_activity', 'configure_netboot',
    'Command', 'HTTP');

INSERT INTO command_queue (id, updated, system_id, kernel_options)
VALUES (2, '2016-02-16 01:30:00', 1, 'bad');

-- And here is another configure_netboot command which might have been 
-- triggered for a system with release action ReProvision. Note this one has 
-- service Scheduler but not the callback.

INSERT INTO activity (id, user_id, created, type, action, field_name, service)
VALUES (3, 1, '2016-02-16 01:59:59', 'command_activity', 'configure_netboot',
    'Command', 'Scheduler');

INSERT INTO command_queue (id, updated, system_id, kernel_options)
VALUES (3, '2016-02-16 01:59:59', 1, 'alsobad');

-- Recipe 2 is a guest_recipe with a guest_resource.

INSERT INTO rendered_kickstart (id, kickstart)
VALUES (2, 'lol2');

INSERT INTO recipe (id, type, recipe_set_id, autopick_random, status,
    distro_tree_id, start_time, finish_time, rendered_kickstart_id)
VALUES (2, 'guest_recipe', 1, FALSE, 'Completed',
    1, '2016-02-16 01:30:00', '2016-02-16 02:00:00', 2);

INSERT INTO guest_recipe (id) VALUES (2);

INSERT INTO recipe_resource (id, type, recipe_id, rebooted, install_started,
    install_finished, postinstall_finished)
VALUES (2, 'guest', 2, NULL, '2016-02-16 01:31:00',
    '2016-02-16 01:40:00', '2016-02-16 01:41:00');

INSERT INTO guest_resource (id) VALUES (2);

INSERT INTO machine_guest_map (guest_recipe_id, machine_recipe_id)
VALUES (2, 1);

-- Recipe set 2 has a host recipe (3) and a guest recipe (4), but was cancelled 
-- before they started.

INSERT INTO recipe_set (id, job_id, queue_time, status)
VALUES (2, 1, '2016-02-16 00:00:00', 'Completed');

INSERT INTO rendered_kickstart (id, kickstart)
VALUES (3, 'lol3');

INSERT INTO recipe (id, type, recipe_set_id, autopick_random, status,
    distro_tree_id, start_time, finish_time, rendered_kickstart_id)
VALUES (3, 'machine_recipe', 2, FALSE, 'Cancelled', 1, NULL, NULL, 3);

INSERT INTO machine_recipe (id) VALUES (3);

INSERT INTO reservation (id, user_id, system_id, type, start_time, finish_time)
VALUES (2, 1, 1, 'recipe', '2016-02-17 00:00:00', '2016-02-17 00:00:01');

INSERT INTO recipe_resource (id, type, recipe_id) VALUES (3, 'system', 3);

INSERT INTO system_resource (id, system_id, reservation_id) VALUES (3, 1, 2);

INSERT INTO rendered_kickstart (id, kickstart)
VALUES (4, 'lol4');

INSERT INTO recipe (id, type, recipe_set_id, autopick_random, status,
    distro_tree_id, start_time, finish_time, rendered_kickstart_id)
VALUES (4, 'guest_recipe', 2, FALSE, 'Cancelled', 1, NULL, NULL, 4);

INSERT INTO guest_recipe (id) VALUES (4);

INSERT INTO recipe_resource (id, type, recipe_id) VALUES (4, 'guest', 4);

INSERT INTO guest_resource (id) VALUES (4);

INSERT INTO machine_guest_map (guest_recipe_id, machine_recipe_id)
VALUES (4, 3);
