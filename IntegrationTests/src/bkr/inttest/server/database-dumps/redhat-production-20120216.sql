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
  CONSTRAINT `activity_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3041689 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity`
--


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
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8;
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
  PRIMARY KEY (`id`,`tag`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `beaker_tag`
--


--
-- Table structure for table `breed`
--

DROP TABLE IF EXISTS `breed`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `breed` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `breed` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `breed` (`breed`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `breed`
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
  `status_id` int(11) NOT NULL,
  `task_id` varchar(255) DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `status_id` (`status_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `command_queue_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `command_queue_ibfk_2` FOREIGN KEY (`status_id`) REFERENCES `command_status` (`id`),
  CONSTRAINT `command_queue_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `command_queue`
--


--
-- Table structure for table `command_status`
--

DROP TABLE IF EXISTS `command_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `command_status` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` varchar(255) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `command_status`
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
) ENGINE=InnoDB AUTO_INCREMENT=4779 DEFAULT CHARSET=utf8;
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
  `flag` varchar(10) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cpu_id` (`cpu_id`),
  CONSTRAINT `cpu_flag_ibfk_2` FOREIGN KEY (`cpu_id`) REFERENCES `cpu` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=189978 DEFAULT CHARSET=utf8;
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
  `vendor_id` varchar(255) DEFAULT NULL,
  `device_id` varchar(255) DEFAULT NULL,
  `subsys_device_id` varchar(255) DEFAULT NULL,
  `subsys_vendor_id` varchar(255) DEFAULT NULL,
  `bus` varchar(255) DEFAULT NULL,
  `driver` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `device_class_id` int(11) NOT NULL,
  `date_added` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `device_class_id` (`device_class_id`),
  CONSTRAINT `device_ibfk_1` FOREIGN KEY (`device_class_id`) REFERENCES `device_class` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7779 DEFAULT CHARSET=utf8;
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
  `device_class` varchar(24) DEFAULT NULL,
  `description` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_class`
--


--
-- Table structure for table `distro`
--

DROP TABLE IF EXISTS `distro`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `install_name` varchar(255) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `breed_id` int(11) DEFAULT NULL,
  `osversion_id` int(11) DEFAULT NULL,
  `arch_id` int(11) DEFAULT NULL,
  `variant` varchar(25) DEFAULT NULL,
  `method` varchar(25) DEFAULT NULL,
  `virt` tinyint(1) DEFAULT NULL,
  `date_created` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `install_name` (`install_name`),
  KEY `osversion_id` (`osversion_id`),
  KEY `breed_id` (`breed_id`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `distro_ibfk_1` FOREIGN KEY (`breed_id`) REFERENCES `breed` (`id`),
  CONSTRAINT `distro_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `distro_ibfk_3` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=57487 DEFAULT CHARSET=utf8;
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
  KEY `distro_id` (`distro_id`),
  CONSTRAINT `distro_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `distro_activity_ibfk_2` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_activity`
--


--
-- Table structure for table `distro_lab_controller_map`
--

DROP TABLE IF EXISTS `distro_lab_controller_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_lab_controller_map` (
  `distro_id` int(11) NOT NULL,
  `lab_controller_id` int(11) NOT NULL,
  `tree_path` varchar(1024) DEFAULT NULL,
  PRIMARY KEY (`distro_id`,`lab_controller_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  CONSTRAINT `distro_lab_controller_map_ibfk_1` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `distro_lab_controller_map_ibfk_2` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_lab_controller_map`
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
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8;
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
  KEY `distro_tag_id` (`distro_tag_id`),
  CONSTRAINT `distro_tag_map_ibfk_1` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `distro_tag_map_ibfk_2` FOREIGN KEY (`distro_tag_id`) REFERENCES `distro_tag` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tag_map`
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
) ENGINE=InnoDB AUTO_INCREMENT=11093 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=7120 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_osversion`
--


--
-- Table structure for table `group_activity`
--

DROP TABLE IF EXISTS `group_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `group_activity` (
  `id` int(11) NOT NULL,
  `group_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `group_id` (`group_id`),
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
-- Table structure for table `hypervisor`
--

DROP TABLE IF EXISTS `hypervisor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `hypervisor` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `hypervisor` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `hypervisor`
--


--
-- Table structure for table `install`
--

DROP TABLE IF EXISTS `install`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `install` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `install`
--


--
-- Table structure for table `job`
--

DROP TABLE IF EXISTS `job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `owner_id` int(11) DEFAULT NULL,
  `whiteboard` varchar(2000) DEFAULT NULL,
  `result_id` int(11) DEFAULT NULL,
  `status_id` int(11) DEFAULT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  `retention_tag_id` int(11) DEFAULT NULL,
  `product_id` varchar(100) DEFAULT NULL,
  `deleted` datetime DEFAULT NULL,
  `to_delete` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_job_owner_id` (`owner_id`),
  KEY `retention_tag_id` (`retention_tag_id`),
  KEY `result_id` (`result_id`),
  KEY `status_id` (`status_id`),
  CONSTRAINT `job_ibfk_1` FOREIGN KEY (`retention_tag_id`) REFERENCES `retention_tag` (`id`),
  CONSTRAINT `job_ibfk_2` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `job_ibfk_3` FOREIGN KEY (`result_id`) REFERENCES `task_result` (`id`),
  CONSTRAINT `job_ibfk_4` FOREIGN KEY (`status_id`) REFERENCES `task_status` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=193595 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job`
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
) ENGINE=InnoDB AUTO_INCREMENT=52 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=36126 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=559281 DEFAULT CHARSET=utf8;
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
  `username` varchar(255) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `distros_md5` varchar(40) DEFAULT NULL,
  `systems_md5` varchar(40) DEFAULT NULL,
  `disabled` tinyint(1) DEFAULT '0',
  `removed` datetime DEFAULT NULL,
  `user_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `fqdn` (`fqdn`),
  KEY `lab_controller_user_id` (`user_id`),
  CONSTRAINT `lab_controller_user_id` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lab_controller`
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
) ENGINE=InnoDB AUTO_INCREMENT=50 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `labinfo`
--


--
-- Table structure for table `locked`
--

DROP TABLE IF EXISTS `locked`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `locked` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `locked`
--


--
-- Table structure for table `log_recipe`
--

DROP TABLE IF EXISTS `log_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) DEFAULT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_id_id` (`recipe_id`,`id`),
  KEY `recipe_id` (`recipe_id`)
) ENGINE=InnoDB AUTO_INCREMENT=38331754 DEFAULT CHARSET=utf8;
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
  `recipe_task_id` int(11) DEFAULT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id_id` (`recipe_task_id`,`id`),
  KEY `recipe_task_id` (`recipe_task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=47038686 DEFAULT CHARSET=utf8;
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
  `recipe_task_result_id` int(11) DEFAULT NULL,
  `path` text,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text,
  `basepath` text,
  PRIMARY KEY (`id`),
  KEY `recipe_task_result_id_id` (`recipe_task_result_id`,`id`),
  KEY `recipe_task_result_id` (`recipe_task_result_id`)
) ENGINE=InnoDB AUTO_INCREMENT=95540940 DEFAULT CHARSET=utf8;
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
  PRIMARY KEY (`id`),
  KEY `ix_note_system_id` (`system_id`),
  KEY `ix_note_user_id` (`user_id`),
  CONSTRAINT `note_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `note_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=635 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=1302 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `numa`
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
) ENGINE=InnoDB AUTO_INCREMENT=33 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osmajor`
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
) ENGINE=InnoDB AUTO_INCREMENT=109 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
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
  PRIMARY KEY (`id`),
  KEY `power_type_id` (`power_type_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `power_ibfk_1` FOREIGN KEY (`power_type_id`) REFERENCES `power_type` (`id`),
  CONSTRAINT `power_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1769 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=247 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=6621 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=3935 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
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
  `recipe_set_id` int(11) DEFAULT NULL,
  `distro_id` int(11) DEFAULT NULL,
  `system_id` int(11) DEFAULT NULL,
  `result_id` int(11) DEFAULT NULL,
  `status_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `_host_requires` text,
  `_distro_requires` text,
  `kickstart` text,
  `type` varchar(30) NOT NULL,
  `ttasks` int(11) DEFAULT NULL,
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
  `autopick_random` tinyint(4) DEFAULT '0',
  `reservation_id` int(11) DEFAULT NULL,
  `log_server` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_set_id` (`recipe_set_id`),
  KEY `status_id` (`status_id`),
  KEY `distro_id` (`distro_id`),
  KEY `result_id` (`result_id`),
  KEY `recipe_system_time` (`system_id`,`start_time`),
  KEY `recipe_reservation_id_fk` (`reservation_id`),
  KEY `recipe_log_server` (`log_server`(255)),
  CONSTRAINT `recipe_ibfk_1` FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`),
  CONSTRAINT `recipe_ibfk_2` FOREIGN KEY (`status_id`) REFERENCES `task_status` (`id`),
  CONSTRAINT `recipe_ibfk_3` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `recipe_ibfk_4` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`),
  CONSTRAINT `recipe_ibfk_5` FOREIGN KEY (`result_id`) REFERENCES `task_result` (`id`),
  CONSTRAINT `recipe_reservation_id_fk` FOREIGN KEY (`reservation_id`) REFERENCES `reservation` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=409123 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=1113 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=146017 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_repo`
--


--
-- Table structure for table `recipe_role`
--

DROP TABLE IF EXISTS `recipe_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_role` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) DEFAULT NULL,
  `role` varchar(255) DEFAULT NULL,
  `system_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `recipe_role_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `recipe_role_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=604488 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_role`
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
  `job_id` int(11) DEFAULT NULL,
  `priority_id` int(11) DEFAULT NULL,
  `queue_time` datetime NOT NULL,
  `result_id` int(11) DEFAULT NULL,
  `status_id` int(11) DEFAULT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `priority_id` (`priority_id`),
  KEY `job_id` (`job_id`),
  KEY `result_id` (`result_id`),
  KEY `status_id` (`status_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  CONSTRAINT `recipe_set_ibfk_1` FOREIGN KEY (`priority_id`) REFERENCES `task_priority` (`id`),
  CONSTRAINT `recipe_set_ibfk_2` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`),
  CONSTRAINT `recipe_set_ibfk_3` FOREIGN KEY (`result_id`) REFERENCES `task_result` (`id`),
  CONSTRAINT `recipe_set_ibfk_4` FOREIGN KEY (`status_id`) REFERENCES `task_status` (`id`),
  CONSTRAINT `recipe_set_ibfk_5` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=333016 DEFAULT CHARSET=utf8;
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
  `created` datetime DEFAULT NULL,
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
  `task_id` int(11) NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `result_id` int(11) DEFAULT NULL,
  `status_id` int(11) DEFAULT NULL,
  `role` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `status_id` (`status_id`),
  KEY `result_id` (`result_id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `recipe_task_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `recipe_task_ibfk_2` FOREIGN KEY (`status_id`) REFERENCES `task_status` (`id`),
  CONSTRAINT `recipe_task_ibfk_3` FOREIGN KEY (`result_id`) REFERENCES `task_result` (`id`),
  CONSTRAINT `recipe_task_ibfk_4` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4580457 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=1759869 DEFAULT CHARSET=utf8;
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
  `result_id` int(11) DEFAULT NULL,
  `score` decimal(10,2) DEFAULT NULL,
  `log` text,
  `start_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  KEY `result_id` (`result_id`),
  CONSTRAINT `recipe_task_result_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`),
  CONSTRAINT `recipe_task_result_ibfk_2` FOREIGN KEY (`result_id`) REFERENCES `task_result` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24977317 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_result`
--


--
-- Table structure for table `recipe_task_role`
--

DROP TABLE IF EXISTS `recipe_task_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_role` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) DEFAULT NULL,
  `role` varchar(255) DEFAULT NULL,
  `system_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `recipe_task_role_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`),
  CONSTRAINT `recipe_task_role_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4920018 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_role`
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
-- Table structure for table `release_action`
--

DROP TABLE IF EXISTS `release_action`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `release_action` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `action` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `release_action`
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
) ENGINE=InnoDB AUTO_INCREMENT=528150 DEFAULT CHARSET=utf8;
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
  `needs_product` tinyint(4) DEFAULT '0',
  `expire_in_days` int(8) DEFAULT '0',
  PRIMARY KEY (`id`),
  CONSTRAINT `retention_tag_ibfk_1` FOREIGN KEY (`id`) REFERENCES `beaker_tag` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `retention_tag`
--


--
-- Table structure for table `serial`
--

DROP TABLE IF EXISTS `serial`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `serial` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `serial`
--


--
-- Table structure for table `serial_type`
--

DROP TABLE IF EXISTS `serial_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `serial_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `serial_type`
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
) ENGINE=InnoDB AUTO_INCREMENT=94 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sshpubkey`
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
  `owner_id` int(11) DEFAULT NULL,
  `user_id` int(11) DEFAULT NULL,
  `type_id` int(11) NOT NULL,
  `status_id` int(11) NOT NULL,
  `shared` tinyint(1) DEFAULT NULL,
  `private` tinyint(1) DEFAULT NULL,
  `deleted` tinyint(1) DEFAULT NULL,
  `memory` int(11) DEFAULT NULL,
  `checksum` varchar(32) DEFAULT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `mac_address` varchar(18) DEFAULT NULL,
  `loan_id` int(11) DEFAULT NULL,
  `reprovision_distro_id` int(11) DEFAULT NULL,
  `release_action_id` int(11) DEFAULT NULL,
  `status_reason` varchar(255) DEFAULT NULL,
  `hypervisor_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `owner_id` (`owner_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  KEY `loan_id` (`loan_id`),
  KEY `user_id` (`user_id`),
  KEY `type_id` (`type_id`),
  KEY `status_id` (`status_id`),
  KEY `release_action_id` (`release_action_id`),
  KEY `reprovision_distro_id` (`reprovision_distro_id`),
  KEY `system_hypervisor_id` (`hypervisor_id`),
  CONSTRAINT `system_hypervisor_id` FOREIGN KEY (`hypervisor_id`) REFERENCES `hypervisor` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_ibfk_1` FOREIGN KEY (`reprovision_distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `system_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_3` FOREIGN KEY (`type_id`) REFERENCES `system_type` (`id`),
  CONSTRAINT `system_ibfk_4` FOREIGN KEY (`status_id`) REFERENCES `system_status` (`id`),
  CONSTRAINT `system_ibfk_5` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_6` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`),
  CONSTRAINT `system_ibfk_7` FOREIGN KEY (`loan_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_8` FOREIGN KEY (`release_action_id`) REFERENCES `release_action` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3580 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system`
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
  KEY `system_id` (`system_id`),
  CONSTRAINT `system_activity_ibfk_2` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `system_activity_ibfk_3` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_activity`
--


--
-- Table structure for table `system_admin_map`
--

DROP TABLE IF EXISTS `system_admin_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_admin_map` (
  `system_id` int(11) NOT NULL DEFAULT '0',
  `group_id` int(11) NOT NULL DEFAULT '0',
  PRIMARY KEY (`system_id`,`group_id`),
  KEY `group_id` (`group_id`),
  CONSTRAINT `system_admin_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_admin_map_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_admin_map`
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
-- Table structure for table `system_status`
--

DROP TABLE IF EXISTS `system_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_status` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_status`
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
  `status_id` int(11) NOT NULL,
  `start_time` datetime NOT NULL,
  `finish_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `status_id` (`status_id`),
  KEY `ix_system_status_duration_start_time` (`start_time`),
  KEY `ix_system_status_duration_finish_time` (`finish_time`),
  CONSTRAINT `system_status_duration_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`),
  CONSTRAINT `system_status_duration_ibfk_2` FOREIGN KEY (`status_id`) REFERENCES `system_status` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13911 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_status_duration`
--


--
-- Table structure for table `system_type`
--

DROP TABLE IF EXISTS `system_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` varchar(100) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_type`
--


--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(2048) DEFAULT NULL,
  `rpm` varchar(2048) DEFAULT NULL,
  `oldrpm` varchar(2048) DEFAULT NULL,
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
  `owner` text,
  `version` varchar(256) DEFAULT NULL,
  `license` varchar(256) DEFAULT NULL,
  `valid` tinyint(4) DEFAULT '1',
  PRIMARY KEY (`id`),
  KEY `task_uploader_id_fk` (`uploader_id`),
  KEY `owner` (`owner`(255)),
  KEY `priority` (`priority`(255)),
  CONSTRAINT `task_uploader_id_fk` FOREIGN KEY (`uploader_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=8597 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=17192 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=21271 DEFAULT CHARSET=utf8;
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
) ENGINE=InnoDB AUTO_INCREMENT=88592 DEFAULT CHARSET=utf8;
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
  `package` varchar(2048) CHARACTER SET utf8 COLLATE utf8_bin DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=111260 DEFAULT CHARSET=utf8;
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
-- Table structure for table `task_priority`
--

DROP TABLE IF EXISTS `task_priority`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_priority` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `priority` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_priority`
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
  KEY `task_id` (`task_id`)
) ENGINE=InnoDB AUTO_INCREMENT=795 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_property_needed`
--


--
-- Table structure for table `task_result`
--

DROP TABLE IF EXISTS `task_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `result` varchar(20) DEFAULT NULL,
  `severity` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_result`
--


--
-- Table structure for table `task_status`
--

DROP TABLE IF EXISTS `task_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_status` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `status` varchar(20) DEFAULT NULL,
  `severity` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_status`
--


--
-- Table structure for table `task_type`
--

DROP TABLE IF EXISTS `task_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_type` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type` varchar(256) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8;
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
  `group_name` varchar(16) DEFAULT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `created` datetime DEFAULT NULL,
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `group_name` (`group_name`)
) ENGINE=InnoDB AUTO_INCREMENT=88 DEFAULT CHARSET=utf8;
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
  `password` varchar(40) DEFAULT NULL,
  `created` datetime DEFAULT NULL,
  `disabled` tinyint(1) DEFAULT '0',
  `removed` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  UNIQUE KEY `email_address` (`email_address`)
) ENGINE=InnoDB AUTO_INCREMENT=1752 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tg_user`
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
-- Table structure for table `visit`
--

DROP TABLE IF EXISTS `visit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `visit` (
  `visit_key` varchar(40) NOT NULL,
  `created` datetime NOT NULL,
  `expiry` datetime DEFAULT NULL,
  PRIMARY KEY (`visit_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visit`
--


--
-- Table structure for table `visit_identity`
--

DROP TABLE IF EXISTS `visit_identity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `visit_identity` (
  `visit_key` varchar(40) NOT NULL,
  `user_id` int(11) NOT NULL,
  `proxied_by_user_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`visit_key`),
  KEY `ix_visit_identity_user_id` (`user_id`),
  KEY `proxied_by_user_id` (`proxied_by_user_id`),
  CONSTRAINT `visit_identity_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `visit_identity_ibfk_2` FOREIGN KEY (`proxied_by_user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `visit_identity`
--


--
-- Table structure for table `watchdog`
--

DROP TABLE IF EXISTS `watchdog`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `watchdog` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `system_id` int(11) NOT NULL,
  `recipe_id` int(11) NOT NULL,
  `recipetask_id` int(11) DEFAULT NULL,
  `subtask` varchar(255) DEFAULT NULL,
  `kill_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `recipetask_id` (`recipetask_id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `watchdog_ibfk_2` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `watchdog_ibfk_3` FOREIGN KEY (`recipetask_id`) REFERENCES `recipe_task` (`id`),
  CONSTRAINT `watchdog_ibfk_4` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=375830 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watchdog`
--

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2012-03-20 10:12:58
