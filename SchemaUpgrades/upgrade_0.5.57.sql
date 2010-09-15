ALTER TABLE watchdog MODIFY system_id int(11) NOT NULL;
UPDATE system_status SET status = 'Automated' WHERE id =1;INSERT INTO system_status (status) VALUES('Manual');

