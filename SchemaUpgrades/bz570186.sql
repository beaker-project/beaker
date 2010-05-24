use beaker;
CREATE TABLE `system_admin_map` (
    `system_id` int(11) NOT NULL,
    `group_id` int(11) NOT NULL,
    UNIQUE KEY `sys_id_group_id` (`system_id`,`group_id`),
    KEY `group_id` (`group_id`),
    CONSTRAINT `system_admin_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE,
    CONSTRAINT `system_admin_map_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE,
) ENGINE=InnoDB DEFAULT CHARSET=utf8  

