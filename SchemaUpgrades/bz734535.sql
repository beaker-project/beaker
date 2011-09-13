ALTER TABLE log_recipe CHANGE server server_url text;
ALTER TABLE log_recipe ADD COLUMN server varchar(256);
ALTER TABLE log_recipe ADD INDEX `log_recipe_server` (server);

ALTER TABLE log_recipe_task CHANGE server server_url text;
ALTER TABLE log_recipe_task ADD COLUMN server varchar(256);
ALTER TABLE log_recipe_task ADD INDEX `log_recipe_task_server` (server);

ALTER TABLE log_recipe_task_result CHANGE server server_url text;
ALTER TABLE log_recipe_task_result ADD COLUMN server varchar(256);
ALTER TABLE log_recipe_task_result ADD INDEX `log_recipe_task_result_server` (server);

# For every lab controller you have, This could take a while..
UPDATE log_recipe SET server = 'lab.example.com' WHERE server_url like '%lab.example.com%';
UPDATE log_recipe_task SET server = 'lab.example.com' WHERE server_url like '%lab.example.com%';
UPDATE log_recipe_task_result SET server = 'lab.example.com' WHERE server_url like '%lab.example.com%';
