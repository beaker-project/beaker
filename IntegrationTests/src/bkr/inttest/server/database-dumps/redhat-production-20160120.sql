-- This is derived from a database dump from the Red Hat production Beaker instance,
-- edited to remove all data.

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `activity`
--

DROP TABLE IF EXISTS `activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `activity` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `created` datetime NOT NULL,
  `type` varchar(40) NOT NULL,
  `field_name` varchar(40) NOT NULL,
  `service` varchar(100) NOT NULL,
  `action` varchar(40) NOT NULL,
  `old_value` varchar(60) DEFAULT NULL,
  `new_value` varchar(60) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_activity_user_id` (`user_id`),
  KEY `ix_activity_created` (`created`),
  KEY `ix_activity_action` (`action`),
  KEY `ix_activity_field_name` (`field_name`),
  KEY `ix_activity_service` (`service`),
  KEY `ix_activity_type` (`type`),
  CONSTRAINT `activity_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=33152517 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity`
--


--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL
) ENGINE=MyISAM DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('171c07fb4970');
/*!40000 ALTER TABLE `alembic_version` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `arch`
--

DROP TABLE IF EXISTS `arch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `arch` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `arch` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `arch` (`arch`)
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `arch`
--


--
-- Table structure for table `beaker_tag`
--

DROP TABLE IF EXISTS `beaker_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `beaker_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(20) NOT NULL,
  `type` varchar(40) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tag` (`tag`,`type`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `beaker_tag`
--


--
-- Table structure for table `command_queue`
--

DROP TABLE IF EXISTS `command_queue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `command_queue` (
  `id` int(11) NOT NULL,
  `system_id` int(11) NOT NULL,
  `status` enum('Queued','Running','Completed','Failed','Aborted') NOT NULL,
  `task_id` varchar(255) DEFAULT NULL,
  `delay_until` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `callback` varchar(255) DEFAULT NULL,
  `distro_tree_id` int(11) DEFAULT NULL,
  `kernel_options` text,
  `quiescent_period` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `command_queue_distro_tree_id_fk` (`distro_tree_id`),
  KEY `status` (`status`),
  CONSTRAINT `command_queue_distro_tree_id_fk` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `command_queue_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `command_queue_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `command_queue`
--


--
-- Table structure for table `config_item`
--

DROP TABLE IF EXISTS `config_item`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config_item` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `numeric` tinyint(1) DEFAULT NULL,
  `readonly` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_item`
--


--
-- Table structure for table `config_value_int`
--

DROP TABLE IF EXISTS `config_value_int`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config_value_int` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config_item_id` int(11) NOT NULL,
  `modified` datetime DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `valid_from` datetime DEFAULT NULL,
  `value` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`,`config_item_id`),
  KEY `config_item_id` (`config_item_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `config_value_int_ibfk_1` FOREIGN KEY (`config_item_id`) REFERENCES `config_item` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `config_value_int_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_value_int`
--


--
-- Table structure for table `config_value_string`
--

DROP TABLE IF EXISTS `config_value_string`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `config_value_string` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config_item_id` int(11) NOT NULL,
  `modified` datetime DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  `valid_from` datetime DEFAULT NULL,
  `value` text,
  PRIMARY KEY (`id`,`config_item_id`),
  KEY `config_item_id` (`config_item_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `config_value_string_ibfk_1` FOREIGN KEY (`config_item_id`) REFERENCES `config_item` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `config_value_string_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_value_string`
--


--
-- Table structure for table `cpu`
--

DROP TABLE IF EXISTS `cpu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cpu` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `vendor` varchar(255) DEFAULT NULL,
  `model` int(11) DEFAULT NULL,
  `model_name` varchar(255) DEFAULT NULL,
  `family` int(11) DEFAULT NULL,
  `stepping` int(11) DEFAULT NULL,
  `speed` float DEFAULT NULL,
  `processors` int(11) DEFAULT NULL,
  `cores` int(11) DEFAULT NULL,
  `sockets` int(11) DEFAULT NULL,
  `hyper` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `cpu_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13355 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cpu`
--


--
-- Table structure for table `cpu_flag`
--

DROP TABLE IF EXISTS `cpu_flag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cpu_flag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `cpu_id` int(11) NOT NULL,
  `flag` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cpu_id` (`cpu_id`),
  CONSTRAINT `cpu_flag_ibfk_2` FOREIGN KEY (`cpu_id`) REFERENCES `cpu` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=655028 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cpu_flag`
--


--
-- Table structure for table `device`
--

DROP TABLE IF EXISTS `device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `device` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `vendor_id` varchar(4) DEFAULT NULL,
  `device_id` varchar(4) DEFAULT NULL,
  `subsys_device_id` varchar(4) DEFAULT NULL,
  `subsys_vendor_id` varchar(4) DEFAULT NULL,
  `bus` varchar(255) DEFAULT NULL,
  `driver` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `device_class_id` int(11) NOT NULL,
  `date_added` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `device_uix_1` (`vendor_id`,`device_id`,`subsys_device_id`,`subsys_vendor_id`,`bus`,`driver`,`description`,`device_class_id`),
  KEY `device_class_id` (`device_class_id`),
  KEY `ix_device_driver` (`driver`),
  KEY `ix_device_pciid` (`vendor_id`,`device_id`),
  CONSTRAINT `device_ibfk_1` FOREIGN KEY (`device_class_id`) REFERENCES `device_class` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21925 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device`
--


--
-- Table structure for table `device_class`
--

DROP TABLE IF EXISTS `device_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `device_class` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `device_class` varchar(24) NOT NULL,
  `description` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `device_class` (`device_class`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_class`
--


--
-- Table structure for table `disk`
--

DROP TABLE IF EXISTS `disk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `disk` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `model` varchar(255) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `sector_size` int(11) DEFAULT NULL,
  `phys_sector_size` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `disk_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10371 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `disk`
--


--
-- Table structure for table `distro`
--

DROP TABLE IF EXISTS `distro`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `osversion_id` int(11) NOT NULL,
  `date_created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `distro_osversion_id_fk` (`osversion_id`),
  CONSTRAINT `distro_osversion_id_fk` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6642 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro`
--


--
-- Table structure for table `distro_activity`
--

DROP TABLE IF EXISTS `distro_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_activity` (
  `id` int(11) NOT NULL,
  `distro_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_distro_activity_distro_id` (`distro_id`),
  CONSTRAINT `distro_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `distro_activity_ibfk_2` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_activity`
--


--
-- Table structure for table `distro_tag`
--

DROP TABLE IF EXISTS `distro_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `tag` (`tag`)
) ENGINE=InnoDB AUTO_INCREMENT=253 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tag`
--


--
-- Table structure for table `distro_tag_map`
--

DROP TABLE IF EXISTS `distro_tag_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tag_map` (
  `distro_id` int(11) NOT NULL,
  `distro_tag_id` int(11) NOT NULL,
  PRIMARY KEY (`distro_id`,`distro_tag_id`),
  KEY `distro_tag_map_distro_tag_id_fk` (`distro_tag_id`),
  CONSTRAINT `distro_tag_map_distro_id_fk` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `distro_tag_map_distro_tag_id_fk` FOREIGN KEY (`distro_tag_id`) REFERENCES `distro_tag` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tag_map`
--


--
-- Table structure for table `distro_tree`
--

DROP TABLE IF EXISTS `distro_tree`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `distro_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  `variant` varchar(25) DEFAULT NULL,
  `ks_meta` text,
  `kernel_options` text,
  `kernel_options_post` text,
  `date_created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `distro_id` (`distro_id`,`arch_id`,`variant`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `distro_tree_distro_id_fk` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `distro_tree_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=72082 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree`
--


--
-- Table structure for table `distro_tree_activity`
--

DROP TABLE IF EXISTS `distro_tree_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_activity` (
  `id` int(11) NOT NULL,
  `distro_tree_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_distro_tree_activity_distro_tree_id` (`distro_tree_id`),
  CONSTRAINT `distro_tree_activity_distro_tree_id_fk` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `distro_tree_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_activity`
--


--
-- Table structure for table `distro_tree_image`
--

DROP TABLE IF EXISTS `distro_tree_image`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_image` (
  `distro_tree_id` int(11) NOT NULL,
  `image_type` enum('kernel','initrd','live','uimage','uinitrd') NOT NULL,
  `path` text NOT NULL,
  `kernel_type_id` int(11) NOT NULL,
  PRIMARY KEY (`distro_tree_id`,`image_type`,`kernel_type_id`),
  KEY `distro_tree_image_kernel_type_id_fk` (`kernel_type_id`),
  CONSTRAINT `distro_tree_image_ibfk_1` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `distro_tree_image_kernel_type_id_fk` FOREIGN KEY (`kernel_type_id`) REFERENCES `kernel_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_image`
--


--
-- Table structure for table `distro_tree_lab_controller_map`
--

DROP TABLE IF EXISTS `distro_tree_lab_controller_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_lab_controller_map` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `distro_tree_id` int(11) NOT NULL,
  `lab_controller_id` int(11) NOT NULL,
  `url` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `distro_tree_id` (`distro_tree_id`,`lab_controller_id`,`url`),
  KEY `lab_controller_id` (`lab_controller_id`),
  CONSTRAINT `distro_tree_lab_controller_map_ibfk_1` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `distro_tree_lab_controller_map_ibfk_2` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=179136 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_lab_controller_map`
--


--
-- Table structure for table `distro_tree_repo`
--

DROP TABLE IF EXISTS `distro_tree_repo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_repo` (
  `distro_tree_id` int(11) NOT NULL,
  `repo_id` varchar(255) NOT NULL,
  `repo_type` varchar(255) DEFAULT NULL,
  `path` text NOT NULL,
  PRIMARY KEY (`distro_tree_id`,`repo_id`),
  KEY `ix_distro_tree_repo_repo_type` (`repo_type`),
  CONSTRAINT `distro_tree_repo_ibfk_1` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_repo`
--


--
-- Table structure for table `exclude_osmajor`
--

DROP TABLE IF EXISTS `exclude_osmajor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exclude_osmajor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  `osmajor_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `osmajor_id` (`osmajor_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `exclude_osmajor_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`),
  CONSTRAINT `exclude_osmajor_ibfk_3` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `exclude_osmajor_ibfk_4` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=81070 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_osmajor`
--


--
-- Table structure for table `exclude_osversion`
--

DROP TABLE IF EXISTS `exclude_osversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `exclude_osversion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  `osversion_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `arch_id` (`arch_id`),
  KEY `osversion_id` (`osversion_id`),
  CONSTRAINT `exclude_osversion_ibfk_1` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`),
  CONSTRAINT `exclude_osversion_ibfk_3` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `exclude_osversion_ibfk_4` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=26444 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_osversion`
--


--
-- Table structure for table `external_reports`
--

DROP TABLE IF EXISTS `external_reports`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `external_reports` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `url` varchar(10000) NOT NULL,
  `description` varchar(1000) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `external_reports`
--


--
-- Table structure for table `group_activity`
--

DROP TABLE IF EXISTS `group_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `group_activity` (
  `id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_group_activity_group_id` (`group_id`),
  CONSTRAINT `group_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `group_activity_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `group_activity`
--


--
-- Table structure for table `group_permission`
--

DROP TABLE IF EXISTS `group_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `group_permission` (
  `group_id` int(11) NOT NULL DEFAULT '0',
  `permission_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`group_id`,`permission_id`),
  KEY `group_id` (`group_id`),
  KEY `permission_id` (`permission_id`),
  CONSTRAINT `group_permission_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `group_permission_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `permission` (`permission_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `group_permission`
--


--
-- Table structure for table `guest_recipe`
--

DROP TABLE IF EXISTS `guest_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guest_recipe` (
  `id` int(11) NOT NULL,
  `guestname` text,
  `guestargs` text,
  PRIMARY KEY (`id`),
  CONSTRAINT `guest_recipe_ibfk_1` FOREIGN KEY (`id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `guest_recipe`
--


--
-- Table structure for table `guest_resource`
--

DROP TABLE IF EXISTS `guest_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guest_resource` (
  `id` int(11) NOT NULL,
  `mac_address` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_guest_resource_mac_address` (`mac_address`),
  CONSTRAINT `guest_resource_id_fk` FOREIGN KEY (`id`) REFERENCES `recipe_resource` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `guest_resource`
--


--
-- Table structure for table `hypervisor`
--

DROP TABLE IF EXISTS `hypervisor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hypervisor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hypervisor` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hypervisor`
--


--
-- Table structure for table `job`
--

DROP TABLE IF EXISTS `job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `dirty_version` binary(16) NOT NULL,
  `clean_version` binary(16) NOT NULL,
  `owner_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `whiteboard` varchar(2000) DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted','Reserved') NOT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  `retention_tag_id` int(11) NOT NULL,
  `product_id` int(11) DEFAULT NULL,
  `deleted` datetime DEFAULT NULL,
  `to_delete` datetime DEFAULT NULL,
  `submitter_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_job_owner_id` (`owner_id`),
  KEY `retention_tag_id` (`retention_tag_id`),
  KEY `ix_job_deleted` (`deleted`),
  KEY `ix_job_to_delete` (`to_delete`),
  KEY `ix_job_dirty_clean_version` (`dirty_version`,`clean_version`),
  KEY `job_group_id_fk` (`group_id`),
  KEY `status` (`status`),
  KEY `result` (`result`),
  KEY `job_submitter_id_fk` (`submitter_id`),
  KEY `job_product_id_fk` (`product_id`),
  CONSTRAINT `job_group_id_fk` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`),
  CONSTRAINT `job_ibfk_1` FOREIGN KEY (`retention_tag_id`) REFERENCES `retention_tag` (`id`),
  CONSTRAINT `job_ibfk_2` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `job_product_id_fk` FOREIGN KEY (`product_id`) REFERENCES `product` (`id`),
  CONSTRAINT `job_submitter_id_fk` FOREIGN KEY (`submitter_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1197378 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job`
--


--
-- Table structure for table `job_activity`
--

DROP TABLE IF EXISTS `job_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job_activity` (
  `id` int(11) NOT NULL,
  `job_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `job_id` (`job_id`),
  CONSTRAINT `job_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `job_activity_ibfk_2` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_activity`
--


--
-- Table structure for table `job_cc`
--

DROP TABLE IF EXISTS `job_cc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job_cc` (
  `job_id` int(11) NOT NULL,
  `email_address` varchar(255) NOT NULL,
  PRIMARY KEY (`job_id`,`email_address`),
  KEY `ix_job_cc_email_address` (`email_address`),
  CONSTRAINT `job_cc_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job_cc`
--


--
-- Table structure for table `kernel_type`
--

DROP TABLE IF EXISTS `kernel_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `kernel_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `kernel_type` varchar(100) NOT NULL,
  `uboot` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `kernel_type`
--


--
-- Table structure for table `key_`
--

DROP TABLE IF EXISTS `key_`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `key_` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `key_name` varchar(50) NOT NULL,
  `numeric` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `key_name` (`key_name`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_`
--


--
-- Table structure for table `key_value_int`
--

DROP TABLE IF EXISTS `key_value_int`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `key_value_int` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `key_id` int(11) NOT NULL,
  `key_value` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_key_value_int_system_id` (`system_id`),
  KEY `ix_key_value_int_key_id` (`key_id`),
  CONSTRAINT `key_value_int_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `key_value_int_ibfk_4` FOREIGN KEY (`key_id`) REFERENCES `key_` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=66102 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_value_int`
--


--
-- Table structure for table `key_value_string`
--

DROP TABLE IF EXISTS `key_value_string`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `key_value_string` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `key_id` int(11) NOT NULL,
  `key_value` text NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_key_value_string_system_id` (`system_id`),
  KEY `ix_key_value_string_key_id` (`key_id`),
  CONSTRAINT `key_value_string_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `key_value_string_ibfk_4` FOREIGN KEY (`key_id`) REFERENCES `key_` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1077303 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_value_string`
--


--
-- Table structure for table `lab_controller`
--

DROP TABLE IF EXISTS `lab_controller`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `lab_controller` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fqdn` varchar(255) DEFAULT NULL,
  `disabled` tinyint(1) NOT NULL,
  `removed` datetime DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uc_user_id` (`user_id`),
  UNIQUE KEY `fqdn` (`fqdn`),
  CONSTRAINT `lab_controller_user_id` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lab_controller`
--


--
-- Table structure for table `lab_controller_activity`
--

DROP TABLE IF EXISTS `lab_controller_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `lab_controller_activity` (
  `id` int(11) NOT NULL,
  `lab_controller_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_lab_controller_activity_lab_controller_id` (`lab_controller_id`),
  CONSTRAINT `lab_controller_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `lab_controller_activity_ibfk_2` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lab_controller_activity`
--


--
-- Table structure for table `lab_controller_data_center`
--

DROP TABLE IF EXISTS `lab_controller_data_center`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `lab_controller_data_center` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `lab_controller_id` int(11) NOT NULL,
  `data_center` varchar(255) NOT NULL,
  `storage_domain` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `lab_controller_data_center_lab_controller_id_fk` (`lab_controller_id`),
  CONSTRAINT `lab_controller_data_center_lab_controller_id_fk` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lab_controller_data_center`
--


--
-- Table structure for table `labinfo`
--

DROP TABLE IF EXISTS `labinfo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `labinfo` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `orig_cost` decimal(16,2) DEFAULT NULL,
  `curr_cost` decimal(16,2) DEFAULT NULL,
  `dimensions` varchar(255) DEFAULT NULL,
  `weight` decimal(10,2) DEFAULT NULL,
  `wattage` decimal(10,2) DEFAULT NULL,
  `cooling` decimal(10,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `labinfo_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `labinfo`
--


--
-- Table structure for table `log_recipe`
--

DROP TABLE IF EXISTS `log_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_id_id` (`recipe_id`,`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `fk_log_recipe_recipe_id` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=56561313 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe`
--


--
-- Table structure for table `log_recipe_task`
--

DROP TABLE IF EXISTS `log_recipe_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe_task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) NOT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id_id` (`recipe_task_id`,`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `fk_log_recipe_task_recipe_task_id` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=223482486 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe_task`
--


--
-- Table structure for table `log_recipe_task_result`
--

DROP TABLE IF EXISTS `log_recipe_task_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe_task_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_result_id` int(11) NOT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_task_result_id_id` (`recipe_task_result_id`,`id`),
  KEY `recipe_task_result_id` (`recipe_task_result_id`),
  CONSTRAINT `fk_log_recipe_task_result_recipe_task_result_id` FOREIGN KEY (`recipe_task_result_id`) REFERENCES `recipe_task_result` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=387293160 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe_task_result`
--


--
-- Table structure for table `machine_guest_map`
--

DROP TABLE IF EXISTS `machine_guest_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `machine_guest_map` (
  `machine_recipe_id` int(11) NOT NULL,
  `guest_recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`machine_recipe_id`,`guest_recipe_id`),
  KEY `guest_recipe_id` (`guest_recipe_id`),
  CONSTRAINT `machine_guest_map_ibfk_1` FOREIGN KEY (`machine_recipe_id`) REFERENCES `machine_recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `machine_guest_map_ibfk_2` FOREIGN KEY (`guest_recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `machine_guest_map`
--


--
-- Table structure for table `machine_recipe`
--

DROP TABLE IF EXISTS `machine_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `machine_recipe` (
  `id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `machine_recipe_ibfk_1` FOREIGN KEY (`id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `machine_recipe`
--


--
-- Table structure for table `note`
--

DROP TABLE IF EXISTS `note`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `note` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `created` datetime NOT NULL,
  `text` text NOT NULL,
  `deleted` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_note_system_id` (`system_id`),
  KEY `ix_note_user_id` (`user_id`),
  CONSTRAINT `note_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `note_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=3102 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `note`
--


--
-- Table structure for table `numa`
--

DROP TABLE IF EXISTS `numa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `numa` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `nodes` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `numa_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=10737 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `numa`
--


--
-- Table structure for table `openstack_region`
--

DROP TABLE IF EXISTS `openstack_region`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `openstack_region` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `lab_controller_id` int(11) NOT NULL,
  `ipxe_image_id` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `openstack_region_lab_controller_id_fk` (`lab_controller_id`),
  CONSTRAINT `openstack_region_lab_controller_id_fk` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `openstack_region`
--


--
-- Table structure for table `osmajor`
--

DROP TABLE IF EXISTS `osmajor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `osmajor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `osmajor` varchar(255) DEFAULT NULL,
  `alias` varchar(25) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `osmajor` (`osmajor`),
  UNIQUE KEY `alias` (`alias`)
) ENGINE=InnoDB AUTO_INCREMENT=102 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osmajor`
--


--
-- Table structure for table `osmajor_install_options`
--

DROP TABLE IF EXISTS `osmajor_install_options`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `osmajor_install_options` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `osmajor_id` int(11) NOT NULL,
  `arch_id` int(11) DEFAULT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `osmajor_id` (`osmajor_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `osmajor_install_options_ibfk_1` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `osmajor_install_options_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osmajor_install_options`
--


--
-- Table structure for table `osversion`
--

DROP TABLE IF EXISTS `osversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `osversion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `osmajor_id` int(11) DEFAULT NULL,
  `osminor` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `osversion_uix_1` (`osmajor_id`,`osminor`),
  KEY `osmajor_id` (`osmajor_id`),
  CONSTRAINT `osversion_ibfk_1` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=234 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osversion`
--


--
-- Table structure for table `osversion_arch_map`
--

DROP TABLE IF EXISTS `osversion_arch_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `osversion_arch_map` (
  `osversion_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  PRIMARY KEY (`osversion_id`,`arch_id`),
  KEY `osversion_id` (`osversion_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `osversion_arch_map_ibfk_1` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`),
  CONSTRAINT `osversion_arch_map_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osversion_arch_map`
--


--
-- Table structure for table `permission`
--

DROP TABLE IF EXISTS `permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `permission` (
  `permission_id` int(11) NOT NULL AUTO_INCREMENT,
  `permission_name` varchar(16) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`permission_id`),
  UNIQUE KEY `permission_name` (`permission_name`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `permission`
--


--
-- Table structure for table `power`
--

DROP TABLE IF EXISTS `power`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `power` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `power_type_id` int(11) NOT NULL,
  `system_id` int(11) NOT NULL,
  `power_address` varchar(255) NOT NULL,
  `power_user` varchar(255) DEFAULT NULL,
  `power_passwd` varchar(255) DEFAULT NULL,
  `power_id` varchar(255) DEFAULT NULL,
  `power_quiescent_period` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `power_type_id` (`power_type_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `power_ibfk_1` FOREIGN KEY (`power_type_id`) REFERENCES `power_type` (`id`),
  CONSTRAINT `power_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=5646 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `power`
--


--
-- Table structure for table `power_type`
--

DROP TABLE IF EXISTS `power_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `power_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=58 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `power_type`
--


--
-- Table structure for table `product`
--

DROP TABLE IF EXISTS `product`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `product` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_product_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=487 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product`
--


--
-- Table structure for table `provision`
--

DROP TABLE IF EXISTS `provision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `provision` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  `arch_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `provision_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `provision_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12668 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision`
--


--
-- Table structure for table `provision_family`
--

DROP TABLE IF EXISTS `provision_family`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `provision_family` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `provision_id` int(11) NOT NULL,
  `osmajor_id` int(11) NOT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `provision_id` (`provision_id`),
  KEY `osmajor_id` (`osmajor_id`),
  CONSTRAINT `provision_family_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`),
  CONSTRAINT `provision_family_ibfk_3` FOREIGN KEY (`provision_id`) REFERENCES `provision` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6710 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision_family`
--


--
-- Table structure for table `provision_update_family`
--

DROP TABLE IF EXISTS `provision_update_family`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `provision_update_family` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `provision_family_id` int(11) NOT NULL,
  `osversion_id` int(11) NOT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `provision_family_id` (`provision_family_id`),
  KEY `osversion_id` (`osversion_id`),
  CONSTRAINT `provision_update_family_ibfk_2` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`),
  CONSTRAINT `provision_update_family_ibfk_3` FOREIGN KEY (`provision_family_id`) REFERENCES `provision_family` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=529 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision_update_family`
--


--
-- Table structure for table `recipe`
--

DROP TABLE IF EXISTS `recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_set_id` int(11) NOT NULL,
  `distro_tree_id` int(11) DEFAULT NULL,
  `rendered_kickstart_id` int(11) DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted','Reserved') NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `_host_requires` text,
  `_distro_requires` text,
  `kickstart` text,
  `type` varchar(30) NOT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  `whiteboard` varchar(2000) DEFAULT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  `role` varchar(255) DEFAULT NULL,
  `panic` varchar(20) DEFAULT NULL,
  `_partitions` text,
  `autopick_random` tinyint(1) NOT NULL,
  `log_server` varchar(255) DEFAULT NULL,
  `virt_status` enum('Possible','Precluded','Succeeded','Skipped','Failed') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_set_id` (`recipe_set_id`),
  KEY `recipe_system_time` (`start_time`),
  KEY `recipe_log_server` (`log_server`),
  KEY `recipe_distro_tree_id_fk` (`distro_tree_id`),
  KEY `virt_status` (`virt_status`),
  KEY `recipe_rendered_kickstart_id_fk` (`rendered_kickstart_id`),
  KEY `status` (`status`),
  KEY `result` (`result`),
  CONSTRAINT `recipe_distro_tree_id_fk` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `recipe_ibfk_1` FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`),
  CONSTRAINT `recipe_rendered_kickstart_id_fk` FOREIGN KEY (`rendered_kickstart_id`) REFERENCES `rendered_kickstart` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=2430616 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe`
--


--
-- Table structure for table `recipe_ksappend`
--

DROP TABLE IF EXISTS `recipe_ksappend`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_ksappend` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `ks_append` text,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_ksappend_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=231395 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_ksappend`
--


--
-- Table structure for table `recipe_repo`
--

DROP TABLE IF EXISTS `recipe_repo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_repo` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `url` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_repo_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=530687 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_repo`
--


--
-- Table structure for table `recipe_reservation`
--

DROP TABLE IF EXISTS `recipe_reservation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_reservation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `duration` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_reservation_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18003 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_reservation`
--


--
-- Table structure for table `recipe_resource`
--

DROP TABLE IF EXISTS `recipe_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_resource` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `type` enum('system','virt','guest') NOT NULL,
  `fqdn` varchar(255) DEFAULT NULL,
  `rebooted` datetime DEFAULT NULL,
  `install_started` datetime DEFAULT NULL,
  `install_finished` datetime DEFAULT NULL,
  `postinstall_finished` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `recipe_id` (`recipe_id`),
  KEY `ix_recipe_resource_fqdn` (`fqdn`),
  CONSTRAINT `recipe_resource_recipe_id_fk` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2274728 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_resource`
--


--
-- Table structure for table `recipe_rpm`
--

DROP TABLE IF EXISTS `recipe_rpm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_rpm` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `package` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `release` varchar(255) DEFAULT NULL,
  `epoch` int(11) DEFAULT NULL,
  `arch` varchar(255) DEFAULT NULL,
  `running_kernel` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_rpm_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_rpm`
--


--
-- Table structure for table `recipe_set`
--

DROP TABLE IF EXISTS `recipe_set`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_set` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `job_id` int(11) NOT NULL,
  `priority` enum('Low','Medium','Normal','High','Urgent') NOT NULL,
  `queue_time` datetime NOT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted','Reserved') NOT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `job_id` (`job_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  KEY `status` (`status`),
  KEY `result` (`result`),
  KEY `priority` (`priority`),
  CONSTRAINT `recipe_set_ibfk_2` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`),
  CONSTRAINT `recipe_set_ibfk_5` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1936888 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_set`
--


--
-- Table structure for table `recipe_set_nacked`
--

DROP TABLE IF EXISTS `recipe_set_nacked`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_set_nacked` (
  `recipe_set_id` int(11) NOT NULL,
  `comment` varchar(255) DEFAULT NULL,
  `created` datetime NOT NULL,
  `response_id` int(11) NOT NULL,
  PRIMARY KEY (`recipe_set_id`),
  KEY `response_id` (`response_id`),
  CONSTRAINT `recipe_set_nacked_ibfk_1` FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_set_nacked_ibfk_2` FOREIGN KEY (`response_id`) REFERENCES `response` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_set_nacked`
--


--
-- Table structure for table `recipe_tag`
--

DROP TABLE IF EXISTS `recipe_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_tag` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `tag` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_tag`
--


--
-- Table structure for table `recipe_tag_map`
--

DROP TABLE IF EXISTS `recipe_tag_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_tag_map` (
  `tag_id` int(11) NOT NULL,
  `recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`tag_id`,`recipe_id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_tag_map_ibfk_1` FOREIGN KEY (`tag_id`) REFERENCES `recipe_tag` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_tag_map_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_tag_map`
--


--
-- Table structure for table `recipe_task`
--

DROP TABLE IF EXISTS `recipe_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `name` varchar(255) NOT NULL,
  `version` varchar(255) DEFAULT NULL,
  `fetch_url` varchar(2048) DEFAULT NULL,
  `fetch_subdir` varchar(2048) NOT NULL DEFAULT '',
  `task_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Running','Completed','Cancelled','Aborted','Reserved') NOT NULL,
  `role` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `task_id` (`task_id`),
  KEY `name` (`name`),
  KEY `version` (`version`),
  KEY `name_2` (`name`,`version`),
  CONSTRAINT `recipe_task_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `recipe_task_ibfk_4` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=37415766 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task`
--


--
-- Table structure for table `recipe_task_bugzilla`
--

DROP TABLE IF EXISTS `recipe_task_bugzilla`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_bugzilla` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) DEFAULT NULL,
  `bugzilla_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_bugzilla_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_bugzilla`
--


--
-- Table structure for table `recipe_task_comment`
--

DROP TABLE IF EXISTS `recipe_task_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_comment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) DEFAULT NULL,
  `comment` text,
  `created` datetime DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_recipe_task_comment_user_id` (`user_id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_comment_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`),
  CONSTRAINT `recipe_task_comment_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_comment`
--


--
-- Table structure for table `recipe_task_param`
--

DROP TABLE IF EXISTS `recipe_task_param`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_param` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `value` text,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_param_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=32047862 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_param`
--


--
-- Table structure for table `recipe_task_result`
--

DROP TABLE IF EXISTS `recipe_task_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) DEFAULT NULL,
  `path` varchar(2048) DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None') NOT NULL,
  `score` decimal(10,2) DEFAULT NULL,
  `log` text,
  `start_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_result_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=183745492 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_result`
--


--
-- Table structure for table `recipe_task_rpm`
--

DROP TABLE IF EXISTS `recipe_task_rpm`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_rpm` (
  `recipe_task_id` int(11) NOT NULL,
  `package` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `release` varchar(255) DEFAULT NULL,
  `epoch` int(11) DEFAULT NULL,
  `arch` varchar(255) DEFAULT NULL,
  `running_kernel` tinyint(1) DEFAULT NULL,
  PRIMARY KEY (`recipe_task_id`),
  CONSTRAINT `recipe_task_rpm_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_rpm`
--


--
-- Table structure for table `recipeset_activity`
--

DROP TABLE IF EXISTS `recipeset_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipeset_activity` (
  `id` int(11) NOT NULL,
  `recipeset_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipeset_id` (`recipeset_id`),
  CONSTRAINT `recipeset_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `recipeset_activity_ibfk_2` FOREIGN KEY (`recipeset_id`) REFERENCES `recipe_set` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipeset_activity`
--


--
-- Table structure for table `rendered_kickstart`
--

DROP TABLE IF EXISTS `rendered_kickstart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rendered_kickstart` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `kickstart` text,
  `url` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=1769446 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rendered_kickstart`
--


--
-- Table structure for table `reservation`
--

DROP TABLE IF EXISTS `reservation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reservation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `start_time` datetime NOT NULL,
  `finish_time` datetime DEFAULT NULL,
  `type` varchar(30) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `user_id` (`user_id`),
  KEY `ix_reservation_start_time` (`start_time`),
  KEY `ix_reservation_finish_time` (`finish_time`),
  KEY `ix_reservation_type` (`type`),
  CONSTRAINT `reservation_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`),
  CONSTRAINT `reservation_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2375152 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reservation`
--


--
-- Table structure for table `response`
--

DROP TABLE IF EXISTS `response`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `response` (
  `id` int(7) NOT NULL AUTO_INCREMENT,
  `response` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `response`
--


--
-- Table structure for table `retention_tag`
--

DROP TABLE IF EXISTS `retention_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `retention_tag` (
  `id` int(11) NOT NULL,
  `default_` tinyint(1) DEFAULT NULL,
  `needs_product` tinyint(1) NOT NULL,
  `expire_in_days` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `retention_tag_ibfk_1` FOREIGN KEY (`id`) REFERENCES `beaker_tag` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `retention_tag`
--


--
-- Table structure for table `sshpubkey`
--

DROP TABLE IF EXISTS `sshpubkey`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `sshpubkey` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `keytype` varchar(16) NOT NULL,
  `pubkey` text NOT NULL,
  `ident` varchar(63) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `sshpubkey_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1934 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sshpubkey`
--


--
-- Table structure for table `submission_delegate`
--

DROP TABLE IF EXISTS `submission_delegate`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `submission_delegate` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL,
  `delegate_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`,`delegate_id`),
  KEY `tg_user_id_fk2` (`delegate_id`),
  CONSTRAINT `tg_user_id_fk1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `tg_user_id_fk2` FOREIGN KEY (`delegate_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=174 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `submission_delegate`
--


--
-- Table structure for table `system`
--

DROP TABLE IF EXISTS `system`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `fqdn` varchar(255) NOT NULL,
  `serial` varchar(1024) DEFAULT NULL,
  `date_added` datetime NOT NULL,
  `date_modified` datetime DEFAULT NULL,
  `date_lastcheckin` datetime DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `vendor` varchar(255) DEFAULT NULL,
  `model` varchar(255) DEFAULT NULL,
  `lender` varchar(255) DEFAULT NULL,
  `owner_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `type` enum('Machine','Resource','Laptop','Prototype') NOT NULL,
  `status` enum('Automated','Broken','Manual','Removed') NOT NULL,
  `private` tinyint(1) DEFAULT NULL,
  `deleted` tinyint(1) DEFAULT NULL,
  `memory` int(11) DEFAULT NULL,
  `checksum` varchar(32) DEFAULT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `mac_address` varchar(18) DEFAULT NULL,
  `loan_id` int(11) DEFAULT NULL,
  `reprovision_distro_tree_id` int(11) DEFAULT NULL,
  `release_action` enum('PowerOff','LeaveOn','ReProvision') NOT NULL,
  `status_reason` varchar(4000) DEFAULT NULL,
  `hypervisor_id` int(11) DEFAULT NULL,
  `kernel_type_id` int(11) NOT NULL,
  `loan_comment` varchar(1000) DEFAULT NULL,
  `custom_access_policy_id` int(11) DEFAULT NULL,
  `active_access_policy_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `fqdn` (`fqdn`),
  KEY `owner_id` (`owner_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  KEY `loan_id` (`loan_id`),
  KEY `user_id` (`user_id`),
  KEY `system_hypervisor_id` (`hypervisor_id`),
  KEY `system_reprovision_distro_tree_id_fk` (`reprovision_distro_tree_id`),
  KEY `system_kernel_type_id_fk` (`kernel_type_id`),
  KEY `custom_access_policy_id_fk` (`custom_access_policy_id`),
  KEY `active_access_policy_id_fk` (`active_access_policy_id`),
  CONSTRAINT `active_access_policy_id_fk` FOREIGN KEY (`active_access_policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `custom_access_policy_id_fk` FOREIGN KEY (`custom_access_policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `system_hypervisor_id` FOREIGN KEY (`hypervisor_id`) REFERENCES `hypervisor` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_5` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_6` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`),
  CONSTRAINT `system_ibfk_7` FOREIGN KEY (`loan_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_kernel_type_id_fk` FOREIGN KEY (`kernel_type_id`) REFERENCES `kernel_type` (`id`),
  CONSTRAINT `system_reprovision_distro_tree_id_fk` FOREIGN KEY (`reprovision_distro_tree_id`) REFERENCES `distro_tree` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8179 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system`
--


--
-- Table structure for table `system_access_policy`
--

DROP TABLE IF EXISTS `system_access_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_access_policy` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6873 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_access_policy`
--


--
-- Table structure for table `system_access_policy_rule`
--

DROP TABLE IF EXISTS `system_access_policy_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_access_policy_rule` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `policy_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `permission` enum('edit_policy','edit_system','loan_any','loan_self','control_system','reserve','view','view_power') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_access_policy_rule_policy_id_fk` (`policy_id`),
  KEY `system_access_policy_rule_user_id_fk` (`user_id`),
  KEY `system_access_policy_rule_group_id_fk` (`group_id`),
  CONSTRAINT `system_access_policy_rule_group_id_fk` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`),
  CONSTRAINT `system_access_policy_rule_policy_id_fk` FOREIGN KEY (`policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `system_access_policy_rule_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=50217 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_access_policy_rule`
--


--
-- Table structure for table `system_activity`
--

DROP TABLE IF EXISTS `system_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_activity` (
  `id` int(11) NOT NULL,
  `system_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_system_activity_system_id` (`system_id`),
  CONSTRAINT `system_activity_ibfk_2` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `system_activity_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_activity`
--


--
-- Table structure for table `system_arch_map`
--

DROP TABLE IF EXISTS `system_arch_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_arch_map` (
  `system_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  PRIMARY KEY (`system_id`,`arch_id`),
  KEY `system_id` (`system_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `system_arch_map_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `system_arch_map_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_arch_map`
--


--
-- Table structure for table `system_cc`
--

DROP TABLE IF EXISTS `system_cc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_cc` (
  `system_id` int(11) NOT NULL,
  `email_address` varchar(255) NOT NULL,
  PRIMARY KEY (`system_id`,`email_address`),
  KEY `ix_system_cc_email_address` (`email_address`),
  CONSTRAINT `fk_system_cc_system_id` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_cc`
--


--
-- Table structure for table `system_device_map`
--

DROP TABLE IF EXISTS `system_device_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_device_map` (
  `system_id` int(11) NOT NULL,
  `device_id` int(11) NOT NULL,
  PRIMARY KEY (`system_id`,`device_id`),
  KEY `system_id` (`system_id`),
  KEY `device_id` (`device_id`),
  CONSTRAINT `system_device_map_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `device` (`id`),
  CONSTRAINT `system_device_map_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_device_map`
--


--
-- Table structure for table `system_group`
--

DROP TABLE IF EXISTS `system_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_group` (
  `system_id` int(11) NOT NULL DEFAULT '0',
  `group_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`system_id`,`group_id`),
  KEY `system_id` (`system_id`),
  KEY `group_id` (`group_id`),
  CONSTRAINT `system_group_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_group_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_group`
--


--
-- Table structure for table `system_hardware_scan_recipe_map`
--

DROP TABLE IF EXISTS `system_hardware_scan_recipe_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_hardware_scan_recipe_map` (
  `system_id` int(11) NOT NULL,
  `recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`system_id`,`recipe_id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `system_hardware_scan_recipe_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_hardware_scan_recipe_map_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_hardware_scan_recipe_map`
--


--
-- Table structure for table `system_pool`
--

DROP TABLE IF EXISTS `system_pool`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_pool` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `description` varchar(4000) DEFAULT NULL,
  `owning_group_id` int(11) DEFAULT NULL,
  `owning_user_id` int(11) DEFAULT NULL,
  `access_policy_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `owning_group_id` (`owning_group_id`),
  KEY `owning_user_id` (`owning_user_id`),
  KEY `system_pool_access_policy_id_fk` (`access_policy_id`),
  CONSTRAINT `system_pool_access_policy_id_fk` FOREIGN KEY (`access_policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `system_pool_ibfk_1` FOREIGN KEY (`owning_group_id`) REFERENCES `tg_group` (`group_id`),
  CONSTRAINT `system_pool_ibfk_2` FOREIGN KEY (`owning_user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=170 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_pool`
--


--
-- Table structure for table `system_pool_activity`
--

DROP TABLE IF EXISTS `system_pool_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_pool_activity` (
  `id` int(11) NOT NULL,
  `pool_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `pool_id` (`pool_id`),
  CONSTRAINT `system_pool_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `system_pool_activity_ibfk_2` FOREIGN KEY (`pool_id`) REFERENCES `system_pool` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_pool_activity`
--


--
-- Table structure for table `system_pool_map`
--

DROP TABLE IF EXISTS `system_pool_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_pool_map` (
  `system_id` int(11) NOT NULL,
  `pool_id` int(11) NOT NULL,
  PRIMARY KEY (`system_id`,`pool_id`),
  KEY `pool_id` (`pool_id`),
  CONSTRAINT `system_pool_map_ibfk_1` FOREIGN KEY (`pool_id`) REFERENCES `system_pool` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_pool_map_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_pool_map`
--


--
-- Table structure for table `system_recipe_map`
--

DROP TABLE IF EXISTS `system_recipe_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_recipe_map` (
  `system_id` int(11) NOT NULL,
  `recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`system_id`,`recipe_id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `system_recipe_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_recipe_map_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_recipe_map`
--


--
-- Table structure for table `system_resource`
--

DROP TABLE IF EXISTS `system_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_resource` (
  `id` int(11) NOT NULL,
  `system_id` int(11) NOT NULL,
  `reservation_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_resource_system_id_fk` (`system_id`),
  KEY `system_resource_reservation_id_fk` (`reservation_id`),
  CONSTRAINT `system_resource_id_fk` FOREIGN KEY (`id`) REFERENCES `recipe_resource` (`id`),
  CONSTRAINT `system_resource_reservation_id_fk` FOREIGN KEY (`reservation_id`) REFERENCES `reservation` (`id`),
  CONSTRAINT `system_resource_system_id_fk` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_resource`
--


--
-- Table structure for table `system_status_duration`
--

DROP TABLE IF EXISTS `system_status_duration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_status_duration` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `status` enum('Automated','Broken','Manual','Removed') NOT NULL,
  `start_time` datetime NOT NULL,
  `finish_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `ix_system_status_duration_start_time` (`start_time`),
  KEY `ix_system_status_duration_finish_time` (`finish_time`),
  CONSTRAINT `system_status_duration_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=64528 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_status_duration`
--


--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `rpm` varchar(255) DEFAULT NULL,
  `path` varchar(4096) DEFAULT NULL,
  `description` varchar(2048) DEFAULT NULL,
  `repo` varchar(256) DEFAULT NULL,
  `avg_time` int(11) DEFAULT NULL,
  `destructive` tinyint(1) DEFAULT NULL,
  `priority` varchar(256) DEFAULT NULL,
  `nda` tinyint(1) DEFAULT NULL,
  `creation_date` datetime DEFAULT NULL,
  `update_date` datetime DEFAULT NULL,
  `uploader_id` int(11) DEFAULT NULL,
  `owner` varchar(255) DEFAULT NULL,
  `version` varchar(256) DEFAULT NULL,
  `license` varchar(256) DEFAULT NULL,
  `valid` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `rpm` (`rpm`),
  KEY `task_uploader_id_fk` (`uploader_id`),
  KEY `owner` (`owner`),
  KEY `priority` (`priority`(255)),
  CONSTRAINT `task_uploader_id_fk` FOREIGN KEY (`uploader_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=20967 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task`
--


--
-- Table structure for table `task_bugzilla`
--

DROP TABLE IF EXISTS `task_bugzilla`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_bugzilla` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `bugzilla_id` int(11) DEFAULT NULL,
  `task_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `task_bugzilla_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=83025 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_bugzilla`
--


--
-- Table structure for table `task_exclude_arch`
--

DROP TABLE IF EXISTS `task_exclude_arch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclude_arch` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) DEFAULT NULL,
  `arch_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `task_exclude_arch_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`),
  CONSTRAINT `task_exclude_arch_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=76488 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclude_arch`
--


--
-- Table structure for table `task_exclude_osmajor`
--

DROP TABLE IF EXISTS `task_exclude_osmajor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclude_osmajor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) DEFAULT NULL,
  `osmajor_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  KEY `osmajor_id` (`osmajor_id`),
  CONSTRAINT `task_exclude_osmajor_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`),
  CONSTRAINT `task_exclude_osmajor_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=488882 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclude_osmajor`
--


--
-- Table structure for table `task_package`
--

DROP TABLE IF EXISTS `task_package`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_package` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `package` varchar(255) CHARACTER SET utf8 COLLATE utf8_bin NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `package` (`package`)
) ENGINE=InnoDB AUTO_INCREMENT=117312 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_package`
--


--
-- Table structure for table `task_packages_custom_map`
--

DROP TABLE IF EXISTS `task_packages_custom_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_custom_map` (
  `recipe_id` int(11) NOT NULL DEFAULT '0',
  `package_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`recipe_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_custom_map_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_custom_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_custom_map`
--


--
-- Table structure for table `task_packages_required_map`
--

DROP TABLE IF EXISTS `task_packages_required_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_required_map` (
  `task_id` int(11) NOT NULL DEFAULT '0',
  `package_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`task_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_required_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_required_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_required_map`
--


--
-- Table structure for table `task_packages_runfor_map`
--

DROP TABLE IF EXISTS `task_packages_runfor_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_runfor_map` (
  `task_id` int(11) NOT NULL DEFAULT '0',
  `package_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`task_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_runfor_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_runfor_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_runfor_map`
--


--
-- Table structure for table `task_property_needed`
--

DROP TABLE IF EXISTS `task_property_needed`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_property_needed` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `task_id` int(11) DEFAULT NULL,
  `property` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `task_property_needed_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2335 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_property_needed`
--


--
-- Table structure for table `task_type`
--

DROP TABLE IF EXISTS `task_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `type` (`type`)
) ENGINE=InnoDB AUTO_INCREMENT=103 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_type`
--


--
-- Table structure for table `task_type_map`
--

DROP TABLE IF EXISTS `task_type_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_type_map` (
  `task_id` int(11) NOT NULL DEFAULT '0',
  `task_type_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`task_id`,`task_type_id`),
  KEY `task_type_id` (`task_type_id`),
  CONSTRAINT `task_type_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_type_map_ibfk_2` FOREIGN KEY (`task_type_id`) REFERENCES `task_type` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_type_map`
--


--
-- Table structure for table `tg_group`
--

DROP TABLE IF EXISTS `tg_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tg_group` (
  `group_id` int(11) NOT NULL AUTO_INCREMENT,
  `group_name` varchar(255) NOT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `root_password` varchar(255) DEFAULT NULL,
  `created` datetime DEFAULT NULL,
  `ldap` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `group_name` (`group_name`),
  KEY `ldap` (`ldap`)
) ENGINE=InnoDB AUTO_INCREMENT=236 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tg_group`
--


--
-- Table structure for table `tg_user`
--

DROP TABLE IF EXISTS `tg_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `tg_user` (
  `user_id` int(11) NOT NULL AUTO_INCREMENT,
  `user_name` varchar(255) DEFAULT NULL,
  `email_address` varchar(255) DEFAULT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `password` text,
  `created` datetime DEFAULT NULL,
  `disabled` tinyint(1) NOT NULL,
  `removed` datetime DEFAULT NULL,
  `root_password` varchar(255) DEFAULT NULL,
  `rootpw_changed` datetime DEFAULT NULL,
  `openstack_username` varchar(255) DEFAULT NULL,
  `openstack_password` varchar(2048) DEFAULT NULL,
  `openstack_tenant_name` varchar(2048) DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  KEY `email_address` (`email_address`)
) ENGINE=InnoDB AUTO_INCREMENT=4461 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tg_user`
--


--
-- Table structure for table `user_activity`
--

DROP TABLE IF EXISTS `user_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_activity` (
  `id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `user_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `user_activity_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_activity`
--


--
-- Table structure for table `user_group`
--

DROP TABLE IF EXISTS `user_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_group` (
  `user_id` int(11) NOT NULL DEFAULT '0',
  `group_id` int(11) NOT NULL DEFAULT '0',
  `is_owner` tinyint(1) NOT NULL,
  PRIMARY KEY (`user_id`,`group_id`),
  KEY `user_id` (`user_id`),
  KEY `group_id` (`group_id`),
  CONSTRAINT `user_group_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_group_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_group`
--


--
-- Table structure for table `virt_resource`
--

DROP TABLE IF EXISTS `virt_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `virt_resource` (
  `id` int(11) NOT NULL,
  `instance_id` binary(16) NOT NULL,
  `system_name` varchar(2048) NOT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `kernel_options` varchar(2048) DEFAULT NULL,
  `mac_address` bigint(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `virt_resource_lab_controller_id_fk` (`lab_controller_id`),
  KEY `ix_virt_resource_mac_address` (`mac_address`),
  CONSTRAINT `virt_resource_id_fk` FOREIGN KEY (`id`) REFERENCES `recipe_resource` (`id`),
  CONSTRAINT `virt_resource_lab_controller_id_fk` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `virt_resource`
--


--
-- Table structure for table `watchdog`
--

DROP TABLE IF EXISTS `watchdog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `watchdog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `recipetask_id` int(11) DEFAULT NULL,
  `subtask` varchar(255) DEFAULT NULL,
  `kill_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `recipetask_id` (`recipetask_id`),
  CONSTRAINT `watchdog_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `watchdog_ibfk_3` FOREIGN KEY (`recipetask_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2255626 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watchdog`
--


--
-- Dumping events for database 'beaker'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2016-01-20 23:34:01
