-- Job which is not deleted
INSERT INTO job (id, owner_id, retention_tag_id, dirty_version, clean_version, status)
VALUES (1, 1, 1, '', '', 'Completed');
INSERT INTO recipe_set (id, job_id, queue_time)
VALUES (1, 1, '2016-02-04 01:00:00');
INSERT INTO recipe (id, type, recipe_set_id, autopick_random)
VALUES (1, 'machine_recipe', 1, FALSE);
INSERT INTO recipe_task (id, recipe_id, name, fetch_subdir)
VALUES (1, 1, 'test', '');
INSERT INTO recipe_task_result (id, recipe_task_id)
VALUES (1, 1);
INSERT INTO log_recipe_task_result (id, recipe_task_result_id, path, filename, start_time)
VALUES (1, 1, '/', 'test_log1', '2016-02-06 00:00:00');
-- Job which is deleted
INSERT INTO job (id, owner_id, retention_tag_id, dirty_version, clean_version, status, deleted)
VALUES (2, 1, 1, '', '', 'Completed', '2016-02-05 00:00:00');
INSERT INTO recipe_set (id, job_id, queue_time)
VALUES (2, 2, '2016-02-04 01:00:00');
INSERT INTO recipe (id, type, recipe_set_id, autopick_random)
VALUES (2, 'machine_recipe', 2, FALSE);
INSERT INTO recipe_task (id, recipe_id, name, fetch_subdir)
VALUES (2, 2, 'test', '');
INSERT INTO recipe_task_result (id, recipe_task_id)
VALUES (2, 2);
INSERT INTO log_recipe_task_result (id, recipe_task_result_id, path, filename, start_time)
VALUES (2, 2, '/', 'test_log2', '2016-02-06 01:00:00');
COMMIT;
