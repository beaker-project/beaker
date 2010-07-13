use beaker;
CREATE TABLE `response` (
  `id` int(7) NOT NULL auto_increment,
    `response` varchar(50) NOT NULL,
      PRIMARY KEY  (`id`)
      ) ENGINE=InnoDB AUTO_INCREMENT=0 DEFAULT CHARSET=utf8;

INSERT INTO response values(1,'ack'),(2,'nak');

CREATE TABLE `recipe_set_nacked` (`recipe_set_id` int(11) NOT NULL,   `comment` varchar(255) default NULL,   `created` datetime default NULL,  `response_id` int(11) NOT NULL,   PRIMARY KEY  (`recipe_set_id`),   FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`) ON DELETE CASCADE, FOREIGN KEY (`response_id`) REFERENCES `response` (`id`) ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
