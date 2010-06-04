use beaker;
CREATE TABLE `recipe_set_nacked` (   `recipe_set_id` int(11) NOT NULL,   `comment` varchar(255) default NULL,   `created` datetime default NULL,   PRIMARY KEY  (`recipe_set_id`),   FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`) ON DELETE CASCADE ) ENGINE=InnoDB DEFAULT CHARSET=utf8;

