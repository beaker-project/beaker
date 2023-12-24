-- MySQL dump 10.16  Distrib 10.3.10-MariaDB, for Linux (x86_64)
--
-- Host: beaker-db    Database: beaker
-- ------------------------------------------------------
-- Server version	10.2.22-MariaDB-1:10.2.22+maria~bionic

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
  KEY `ix_activity_action` (`action`),
  KEY `ix_activity_user_id` (`user_id`),
  KEY `ix_activity_field_name` (`field_name`),
  KEY `ix_activity_type` (`type`),
  KEY `ix_activity_service` (`service`),
  KEY `ix_activity_created` (`created`),
  CONSTRAINT `activity_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `activity`
--

LOCK TABLES `activity` WRITE;
/*!40000 ALTER TABLE `activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `alembic_version`
--

LOCK TABLES `alembic_version` WRITE;
/*!40000 ALTER TABLE `alembic_version` DISABLE KEYS */;
INSERT INTO `alembic_version` VALUES ('140c5eea2836');
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

LOCK TABLES `arch` WRITE;
/*!40000 ALTER TABLE `arch` DISABLE KEYS */;
INSERT INTO `arch` VALUES (10,'aarch64'),(11,'arm'),(9,'armhfp'),(1,'i386'),(3,'ia64'),(4,'ppc'),(5,'ppc64'),(6,'ppc64le'),(7,'s390'),(8,'s390x'),(2,'x86_64');
/*!40000 ALTER TABLE `arch` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `beaker_tag`
--

LOCK TABLES `beaker_tag` WRITE;
/*!40000 ALTER TABLE `beaker_tag` DISABLE KEYS */;
INSERT INTO `beaker_tag` VALUES (3,'120days','retention_tag'),(2,'60days','retention_tag'),(4,'active','retention_tag'),(5,'audit','retention_tag'),(1,'scratch','retention_tag');
/*!40000 ALTER TABLE `beaker_tag` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `command_queue`
--

DROP TABLE IF EXISTS `command_queue`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `command_queue` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) DEFAULT NULL,
  `service` varchar(100) NOT NULL,
  `queue_time` datetime NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `system_id` int(11) NOT NULL,
  `action` varchar(40) NOT NULL,
  `status` enum('Queued','Running','Completed','Failed','Aborted') NOT NULL,
  `delay_until` datetime DEFAULT NULL,
  `quiescent_period` int(11) DEFAULT NULL,
  `error_message` varchar(4000) DEFAULT NULL,
  `installation_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  KEY `command_queue_installation_id_fk` (`installation_id`),
  KEY `ix_command_queue_status` (`status`),
  KEY `ix_command_queue_finish_time` (`finish_time`),
  KEY `ix_command_queue_service` (`service`),
  KEY `ix_command_queue_action` (`action`),
  KEY `ix_command_queue_user_id` (`user_id`),
  KEY `ix_command_queue_queue_time` (`queue_time`),
  KEY `ix_command_queue_start_time` (`start_time`),
  CONSTRAINT `command_queue_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `command_queue_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `command_queue_installation_id_fk` FOREIGN KEY (`installation_id`) REFERENCES `installation` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `command_queue`
--

LOCK TABLES `command_queue` WRITE;
/*!40000 ALTER TABLE `command_queue` DISABLE KEYS */;
/*!40000 ALTER TABLE `command_queue` ENABLE KEYS */;
UNLOCK TABLES;

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
  UNIQUE KEY `name` (`name`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`numeric` in (0,1)),
  CONSTRAINT `CONSTRAINT_2` CHECK (`readonly` in (0,1))
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_item`
--

LOCK TABLES `config_item` WRITE;
/*!40000 ALTER TABLE `config_item` DISABLE KEYS */;
INSERT INTO `config_item` VALUES (1,'root_password','Plaintext root password for provisioned systems',0,0),(2,'root_password_validity','Maximum number of days a user\'s root password is valid for',1,0),(3,'guest_name_prefix','Prefix for names of dynamic guests in OpenStack',0,0),(4,'guest_private_network','Network address in CIDR format for private networks of dynamic guests in OpenStack.',0,0);
/*!40000 ALTER TABLE `config_item` ENABLE KEYS */;
UNLOCK TABLES;

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
  PRIMARY KEY (`id`),
  KEY `config_item_id` (`config_item_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `config_value_int_ibfk_1` FOREIGN KEY (`config_item_id`) REFERENCES `config_item` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `config_value_int_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_value_int`
--

LOCK TABLES `config_value_int` WRITE;
/*!40000 ALTER TABLE `config_value_int` DISABLE KEYS */;
/*!40000 ALTER TABLE `config_value_int` ENABLE KEYS */;
UNLOCK TABLES;

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
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `config_item_id` (`config_item_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `config_value_string_ibfk_1` FOREIGN KEY (`config_item_id`) REFERENCES `config_item` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `config_value_string_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `config_value_string`
--

LOCK TABLES `config_value_string` WRITE;
/*!40000 ALTER TABLE `config_value_string` DISABLE KEYS */;
INSERT INTO `config_value_string` VALUES (1,1,'2023-12-24 14:34:08',1,'2023-12-24 14:34:08','beaker'),(2,4,'2023-12-24 14:34:08',1,'2023-12-24 14:34:08','192.168.10.0/24');
/*!40000 ALTER TABLE `config_value_string` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `cpu_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `CONSTRAINT_1` CHECK (`hyper` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cpu`
--

LOCK TABLES `cpu` WRITE;
/*!40000 ALTER TABLE `cpu` DISABLE KEYS */;
/*!40000 ALTER TABLE `cpu` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `cpu_flag_ibfk_1` FOREIGN KEY (`cpu_id`) REFERENCES `cpu` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cpu_flag`
--

LOCK TABLES `cpu_flag` WRITE;
/*!40000 ALTER TABLE `cpu_flag` DISABLE KEYS */;
/*!40000 ALTER TABLE `cpu_flag` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `data_migration`
--

DROP TABLE IF EXISTS `data_migration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `data_migration` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `finish_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `data_migration`
--

LOCK TABLES `data_migration` WRITE;
/*!40000 ALTER TABLE `data_migration` DISABLE KEYS */;
INSERT INTO `data_migration` VALUES (1,'insert-installation-row-for-recipes-before-25-take-2','2023-12-24 14:34:08'),(2,'insert-installation-row-for-scheduled-recipes-before-25','2023-12-24 14:34:08'),(3,'re-purge-old-jobs-with-logs','2023-12-24 14:34:08'),(4,'commands-for-recipe-installations','2023-12-24 14:34:08');
/*!40000 ALTER TABLE `data_migration` ENABLE KEYS */;
UNLOCK TABLES;

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
  `fw_version` varchar(241) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `device_uix_1` (`vendor_id`,`device_id`,`subsys_device_id`,`subsys_vendor_id`,`bus`,`driver`,`description`,`device_class_id`,`fw_version`),
  KEY `device_class_id` (`device_class_id`),
  KEY `ix_device_pciid` (`vendor_id`,`device_id`),
  KEY `ix_device_driver` (`driver`),
  CONSTRAINT `device_ibfk_1` FOREIGN KEY (`device_class_id`) REFERENCES `device_class` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device`
--

LOCK TABLES `device` WRITE;
/*!40000 ALTER TABLE `device` DISABLE KEYS */;
/*!40000 ALTER TABLE `device` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `device_class`
--

DROP TABLE IF EXISTS `device_class`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `device_class` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `device_class` varchar(24) NOT NULL,
  `description` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `device_class` (`device_class`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `device_class`
--

LOCK TABLES `device_class` WRITE;
/*!40000 ALTER TABLE `device_class` DISABLE KEYS */;
/*!40000 ALTER TABLE `device_class` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `disk`
--

LOCK TABLES `disk` WRITE;
/*!40000 ALTER TABLE `disk` DISABLE KEYS */;
/*!40000 ALTER TABLE `disk` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `osversion_id` (`osversion_id`),
  CONSTRAINT `distro_ibfk_1` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro`
--

LOCK TABLES `distro` WRITE;
/*!40000 ALTER TABLE `distro` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `distro_activity`
--

DROP TABLE IF EXISTS `distro_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_activity` (
  `id` int(11) NOT NULL,
  `distro_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_distro_activity_distro_id` (`distro_id`),
  CONSTRAINT `distro_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `distro_activity_ibfk_2` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_activity`
--

LOCK TABLES `distro_activity` WRITE;
/*!40000 ALTER TABLE `distro_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_activity` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tag`
--

LOCK TABLES `distro_tag` WRITE;
/*!40000 ALTER TABLE `distro_tag` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tag` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `distro_tag_map` WRITE;
/*!40000 ALTER TABLE `distro_tag_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tag_map` ENABLE KEYS */;
UNLOCK TABLES;

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
  `ks_meta` text DEFAULT NULL,
  `kernel_options` text DEFAULT NULL,
  `kernel_options_post` text DEFAULT NULL,
  `date_created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `distro_id` (`distro_id`,`arch_id`,`variant`),
  KEY `arch_id` (`arch_id`),
  CONSTRAINT `distro_tree_ibfk_1` FOREIGN KEY (`distro_id`) REFERENCES `distro` (`id`),
  CONSTRAINT `distro_tree_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree`
--

LOCK TABLES `distro_tree` WRITE;
/*!40000 ALTER TABLE `distro_tree` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tree` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `distro_tree_activity`
--

DROP TABLE IF EXISTS `distro_tree_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_activity` (
  `id` int(11) NOT NULL,
  `distro_tree_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_distro_tree_activity_distro_tree_id` (`distro_tree_id`),
  CONSTRAINT `distro_tree_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `distro_tree_activity_ibfk_2` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_activity`
--

LOCK TABLES `distro_tree_activity` WRITE;
/*!40000 ALTER TABLE `distro_tree_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tree_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `distro_tree_image`
--

DROP TABLE IF EXISTS `distro_tree_image`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `distro_tree_image` (
  `distro_tree_id` int(11) NOT NULL,
  `image_type` enum('kernel','initrd','live','uimage','uinitrd') NOT NULL,
  `kernel_type_id` int(11) NOT NULL,
  `path` text NOT NULL,
  PRIMARY KEY (`distro_tree_id`,`image_type`,`kernel_type_id`),
  KEY `kernel_type_id` (`kernel_type_id`),
  CONSTRAINT `distro_tree_image_ibfk_1` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `distro_tree_image_ibfk_2` FOREIGN KEY (`kernel_type_id`) REFERENCES `kernel_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_image`
--

LOCK TABLES `distro_tree_image` WRITE;
/*!40000 ALTER TABLE `distro_tree_image` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tree_image` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `distro_tree_lab_controller_map`
--

LOCK TABLES `distro_tree_lab_controller_map` WRITE;
/*!40000 ALTER TABLE `distro_tree_lab_controller_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tree_lab_controller_map` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `distro_tree_repo` WRITE;
/*!40000 ALTER TABLE `distro_tree_repo` DISABLE KEYS */;
/*!40000 ALTER TABLE `distro_tree_repo` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `arch_id` (`arch_id`),
  KEY `osmajor_id` (`osmajor_id`),
  CONSTRAINT `exclude_osmajor_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `exclude_osmajor_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `exclude_osmajor_ibfk_3` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_osmajor`
--

LOCK TABLES `exclude_osmajor` WRITE;
/*!40000 ALTER TABLE `exclude_osmajor` DISABLE KEYS */;
/*!40000 ALTER TABLE `exclude_osmajor` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `exclude_osversion_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `exclude_osversion_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `exclude_osversion_ibfk_3` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `exclude_osversion`
--

LOCK TABLES `exclude_osversion` WRITE;
/*!40000 ALTER TABLE `exclude_osversion` DISABLE KEYS */;
/*!40000 ALTER TABLE `exclude_osversion` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `excluded_user_group`
--

DROP TABLE IF EXISTS `excluded_user_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `excluded_user_group` (
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  PRIMARY KEY (`user_id`,`group_id`),
  KEY `ix_excluded_user_group_user_id` (`user_id`),
  KEY `ix_excluded_user_group_group_id` (`group_id`),
  CONSTRAINT `excluded_user_group_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `excluded_user_group_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `excluded_user_group`
--

LOCK TABLES `excluded_user_group` WRITE;
/*!40000 ALTER TABLE `excluded_user_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `excluded_user_group` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `group_activity` WRITE;
/*!40000 ALTER TABLE `group_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `group_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `group_permission`
--

DROP TABLE IF EXISTS `group_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `group_permission` (
  `group_id` int(11) NOT NULL,
  `permission_id` int(11) NOT NULL,
  PRIMARY KEY (`group_id`,`permission_id`),
  KEY `ix_group_permission_group_id` (`group_id`),
  KEY `ix_group_permission_permission_id` (`permission_id`),
  CONSTRAINT `group_permission_ibfk_1` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `group_permission_ibfk_2` FOREIGN KEY (`permission_id`) REFERENCES `permission` (`permission_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `group_permission`
--

LOCK TABLES `group_permission` WRITE;
/*!40000 ALTER TABLE `group_permission` DISABLE KEYS */;
INSERT INTO `group_permission` VALUES (1,3),(1,4),(1,5),(2,4),(2,5);
/*!40000 ALTER TABLE `group_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `guest_recipe`
--

DROP TABLE IF EXISTS `guest_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `guest_recipe` (
  `id` int(11) NOT NULL,
  `guestname` text DEFAULT NULL,
  `guestargs` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `guest_recipe_ibfk_1` FOREIGN KEY (`id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `guest_recipe`
--

LOCK TABLES `guest_recipe` WRITE;
/*!40000 ALTER TABLE `guest_recipe` DISABLE KEYS */;
/*!40000 ALTER TABLE `guest_recipe` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `guest_resource` WRITE;
/*!40000 ALTER TABLE `guest_resource` DISABLE KEYS */;
/*!40000 ALTER TABLE `guest_resource` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `hypervisor` WRITE;
/*!40000 ALTER TABLE `hypervisor` DISABLE KEYS */;
INSERT INTO `hypervisor` VALUES (1,'KVM'),(2,'Xen'),(3,'HyperV'),(4,'VMWare');
/*!40000 ALTER TABLE `hypervisor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `installation`
--

DROP TABLE IF EXISTS `installation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `installation` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `distro_tree_id` int(11) DEFAULT NULL,
  `kernel_options` text DEFAULT NULL,
  `rendered_kickstart_id` int(11) DEFAULT NULL,
  `created` datetime NOT NULL,
  `rebooted` datetime DEFAULT NULL,
  `install_started` datetime DEFAULT NULL,
  `install_finished` datetime DEFAULT NULL,
  `postinstall_finished` datetime DEFAULT NULL,
  `system_id` int(11) DEFAULT NULL,
  `recipe_id` int(11) DEFAULT NULL,
  `tree_url` text DEFAULT NULL,
  `initrd_path` text DEFAULT NULL,
  `kernel_path` text DEFAULT NULL,
  `arch_id` int(11) DEFAULT NULL,
  `distro_name` text DEFAULT NULL,
  `osmajor` text DEFAULT NULL,
  `osminor` text DEFAULT NULL,
  `variant` text DEFAULT NULL,
  `image_path` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `installation_distro_tree_id_fk` (`distro_tree_id`),
  KEY `installation_rendered_kickstart_id_fk` (`rendered_kickstart_id`),
  KEY `installation_system_id_fk` (`system_id`),
  KEY `installation_recipe_id_fk` (`recipe_id`),
  KEY `installation_arch_id_fk` (`arch_id`),
  CONSTRAINT `installation_arch_id_fk` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`),
  CONSTRAINT `installation_distro_tree_id_fk` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `installation_recipe_id_fk` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `installation_rendered_kickstart_id_fk` FOREIGN KEY (`rendered_kickstart_id`) REFERENCES `rendered_kickstart` (`id`) ON DELETE SET NULL,
  CONSTRAINT `installation_system_id_fk` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `installation`
--

LOCK TABLES `installation` WRITE;
/*!40000 ALTER TABLE `installation` DISABLE KEYS */;
/*!40000 ALTER TABLE `installation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `job`
--

DROP TABLE IF EXISTS `job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `job` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `is_dirty` tinyint(1) NOT NULL,
  `owner_id` int(11) DEFAULT NULL,
  `submitter_id` int(11) DEFAULT NULL,
  `group_id` int(11) DEFAULT NULL,
  `whiteboard` varchar(4096) DEFAULT NULL,
  `extra_xml` text DEFAULT NULL,
  `retention_tag_id` int(11) NOT NULL,
  `product_id` int(11) DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None','Skip') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Installing','Running','Reserved','Completed','Cancelled','Aborted') NOT NULL,
  `purged` datetime DEFAULT NULL,
  `deleted` datetime DEFAULT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `job_submitter_id_fk` (`submitter_id`),
  KEY `job_group_id_fk` (`group_id`),
  KEY `retention_tag_id` (`retention_tag_id`),
  KEY `product_id` (`product_id`),
  KEY `ix_job_is_dirty` (`is_dirty`),
  KEY `ix_job_deleted` (`deleted`),
  KEY `ix_job_status` (`status`),
  KEY `ix_job_result` (`result`),
  KEY `ix_job_purged` (`purged`),
  KEY `ix_job_owner_id` (`owner_id`),
  CONSTRAINT `job_group_id_fk` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`),
  CONSTRAINT `job_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `job_ibfk_2` FOREIGN KEY (`retention_tag_id`) REFERENCES `retention_tag` (`id`),
  CONSTRAINT `job_ibfk_3` FOREIGN KEY (`product_id`) REFERENCES `product` (`id`),
  CONSTRAINT `job_submitter_id_fk` FOREIGN KEY (`submitter_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`is_dirty` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `job`
--

LOCK TABLES `job` WRITE;
/*!40000 ALTER TABLE `job` DISABLE KEYS */;
/*!40000 ALTER TABLE `job` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `job_activity` WRITE;
/*!40000 ALTER TABLE `job_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `job_activity` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `job_cc` WRITE;
/*!40000 ALTER TABLE `job_cc` DISABLE KEYS */;
/*!40000 ALTER TABLE `job_cc` ENABLE KEYS */;
UNLOCK TABLES;

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
  PRIMARY KEY (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`uboot` in (0,1))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `kernel_type`
--

LOCK TABLES `kernel_type` WRITE;
/*!40000 ALTER TABLE `kernel_type` DISABLE KEYS */;
INSERT INTO `kernel_type` VALUES (1,'default',0),(2,'highbank',0),(3,'imx',0),(4,'omap',0),(5,'tegra',0),(6,'mvebu',1);
/*!40000 ALTER TABLE `kernel_type` ENABLE KEYS */;
UNLOCK TABLES;

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
  UNIQUE KEY `key_name` (`key_name`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`numeric` in (0,1))
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_`
--

LOCK TABLES `key_` WRITE;
/*!40000 ALTER TABLE `key_` DISABLE KEYS */;
INSERT INTO `key_` VALUES (1,'DISKSPACE',1),(2,'COMMENT',0),(3,'CPUFAMILY',1),(4,'CPUFLAGS',0),(5,'CPUMODEL',0),(6,'CPUMODELNUMBER',1),(7,'CPUSPEED',1),(8,'CPUVENDOR',0),(9,'DISK',1),(10,'FORMFACTOR',0),(11,'HVM',0),(12,'MEMORY',1),(13,'MODEL',0),(14,'MODULE',0),(15,'NETWORK',0),(16,'NR_DISKS',1),(17,'NR_ETH',1),(18,'NR_IB',1),(19,'PCIID',0),(20,'PROCESSORS',1),(21,'RTCERT',0),(22,'SCRATCH',0),(23,'STORAGE',0),(24,'USBID',0),(25,'VENDOR',0),(26,'XENCERT',0),(27,'NETBOOT_METHOD',0);
/*!40000 ALTER TABLE `key_` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `ix_key_value_int_key_id` (`key_id`),
  KEY `ix_key_value_int_system_id` (`system_id`),
  CONSTRAINT `key_value_int_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `key_value_int_ibfk_2` FOREIGN KEY (`key_id`) REFERENCES `key_` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_value_int`
--

LOCK TABLES `key_value_int` WRITE;
/*!40000 ALTER TABLE `key_value_int` DISABLE KEYS */;
/*!40000 ALTER TABLE `key_value_int` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `key_value_string_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `key_value_string_ibfk_2` FOREIGN KEY (`key_id`) REFERENCES `key_` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `key_value_string`
--

LOCK TABLES `key_value_string` WRITE;
/*!40000 ALTER TABLE `key_value_string` DISABLE KEYS */;
/*!40000 ALTER TABLE `key_value_string` ENABLE KEYS */;
UNLOCK TABLES;

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
  UNIQUE KEY `user_id` (`user_id`),
  UNIQUE KEY `fqdn` (`fqdn`),
  CONSTRAINT `lab_controller_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`disabled` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `lab_controller`
--

LOCK TABLES `lab_controller` WRITE;
/*!40000 ALTER TABLE `lab_controller` DISABLE KEYS */;
/*!40000 ALTER TABLE `lab_controller` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `lab_controller_activity` WRITE;
/*!40000 ALTER TABLE `lab_controller_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `lab_controller_activity` ENABLE KEYS */;
UNLOCK TABLES;

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
  `weight` decimal(10,0) DEFAULT NULL,
  `wattage` decimal(10,0) DEFAULT NULL,
  `cooling` decimal(10,0) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `system_id` (`system_id`),
  CONSTRAINT `labinfo_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `labinfo`
--

LOCK TABLES `labinfo` WRITE;
/*!40000 ALTER TABLE `labinfo` DISABLE KEYS */;
/*!40000 ALTER TABLE `labinfo` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `log_recipe`
--

DROP TABLE IF EXISTS `log_recipe`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `path` text DEFAULT NULL,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text DEFAULT NULL,
  `basepath` text DEFAULT NULL,
  `recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `log_recipe_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe`
--

LOCK TABLES `log_recipe` WRITE;
/*!40000 ALTER TABLE `log_recipe` DISABLE KEYS */;
/*!40000 ALTER TABLE `log_recipe` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `log_recipe_task`
--

DROP TABLE IF EXISTS `log_recipe_task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe_task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `path` text DEFAULT NULL,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text DEFAULT NULL,
  `basepath` text DEFAULT NULL,
  `recipe_task_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `log_recipe_task_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe_task`
--

LOCK TABLES `log_recipe_task` WRITE;
/*!40000 ALTER TABLE `log_recipe_task` DISABLE KEYS */;
/*!40000 ALTER TABLE `log_recipe_task` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `log_recipe_task_result`
--

DROP TABLE IF EXISTS `log_recipe_task_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `log_recipe_task_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `path` text DEFAULT NULL,
  `filename` text NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `server` text DEFAULT NULL,
  `basepath` text DEFAULT NULL,
  `recipe_task_result_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_result_id` (`recipe_task_result_id`),
  CONSTRAINT `log_recipe_task_result_ibfk_1` FOREIGN KEY (`recipe_task_result_id`) REFERENCES `recipe_task_result` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `log_recipe_task_result`
--

LOCK TABLES `log_recipe_task_result` WRITE;
/*!40000 ALTER TABLE `log_recipe_task_result` DISABLE KEYS */;
/*!40000 ALTER TABLE `log_recipe_task_result` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `machine_guest_map` WRITE;
/*!40000 ALTER TABLE `machine_guest_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `machine_guest_map` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `machine_recipe` WRITE;
/*!40000 ALTER TABLE `machine_recipe` DISABLE KEYS */;
/*!40000 ALTER TABLE `machine_recipe` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `system_id` (`system_id`),
  KEY `ix_note_user_id` (`user_id`),
  CONSTRAINT `note_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `note_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `note`
--

LOCK TABLES `note` WRITE;
/*!40000 ALTER TABLE `note` DISABLE KEYS */;
/*!40000 ALTER TABLE `note` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `numa_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `numa`
--

LOCK TABLES `numa` WRITE;
/*!40000 ALTER TABLE `numa` DISABLE KEYS */;
/*!40000 ALTER TABLE `numa` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `openstack_region`
--

DROP TABLE IF EXISTS `openstack_region`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `openstack_region` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `lab_controller_id` int(11) NOT NULL,
  `ipxe_image_id` binary(16) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `openstack_region_lab_controller_id_fk` (`lab_controller_id`),
  CONSTRAINT `openstack_region_lab_controller_id_fk` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `openstack_region`
--

LOCK TABLES `openstack_region` WRITE;
/*!40000 ALTER TABLE `openstack_region` DISABLE KEYS */;
/*!40000 ALTER TABLE `openstack_region` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osmajor`
--

LOCK TABLES `osmajor` WRITE;
/*!40000 ALTER TABLE `osmajor` DISABLE KEYS */;
/*!40000 ALTER TABLE `osmajor` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osmajor_install_options`
--

LOCK TABLES `osmajor_install_options` WRITE;
/*!40000 ALTER TABLE `osmajor_install_options` DISABLE KEYS */;
/*!40000 ALTER TABLE `osmajor_install_options` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `osversion`
--

DROP TABLE IF EXISTS `osversion`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `osversion` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `osmajor_id` int(11) NOT NULL,
  `osminor` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `osversion_uix_1` (`osmajor_id`,`osminor`),
  KEY `ix_osversion_osmajor_id` (`osmajor_id`),
  CONSTRAINT `osversion_ibfk_1` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osversion`
--

LOCK TABLES `osversion` WRITE;
/*!40000 ALTER TABLE `osversion` DISABLE KEYS */;
/*!40000 ALTER TABLE `osversion` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `ix_osversion_arch_map_osversion_id` (`osversion_id`),
  KEY `ix_osversion_arch_map_arch_id` (`arch_id`),
  CONSTRAINT `osversion_arch_map_ibfk_1` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`),
  CONSTRAINT `osversion_arch_map_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `osversion_arch_map`
--

LOCK TABLES `osversion_arch_map` WRITE;
/*!40000 ALTER TABLE `osversion_arch_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `osversion_arch_map` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `permission`
--

LOCK TABLES `permission` WRITE;
/*!40000 ALTER TABLE `permission` DISABLE KEYS */;
INSERT INTO `permission` VALUES (1,'distro_expire',NULL),(2,'proxy_auth',NULL),(3,'tag_distro',NULL),(4,'stop_task',NULL),(5,'secret_visible',NULL),(6,'change_prio',NULL);
/*!40000 ALTER TABLE `permission` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `power_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `power`
--

LOCK TABLES `power` WRITE;
/*!40000 ALTER TABLE `power` DISABLE KEYS */;
/*!40000 ALTER TABLE `power` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `power_type`
--

LOCK TABLES `power_type` WRITE;
/*!40000 ALTER TABLE `power_type` DISABLE KEYS */;
INSERT INTO `power_type` VALUES (1,'apc_snmp'),(2,'apc_snmp_then_etherwake'),(3,'bladecenter'),(4,'bladepap'),(5,'drac'),(6,'ether_wake'),(7,'hyper-v'),(8,'ilo'),(9,'integrity'),(10,'ipmilan'),(11,'ipmitool'),(12,'lpar'),(13,'rsa'),(14,'virsh'),(15,'wti');
/*!40000 ALTER TABLE `power_type` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `product`
--

LOCK TABLES `product` WRITE;
/*!40000 ALTER TABLE `product` DISABLE KEYS */;
/*!40000 ALTER TABLE `product` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `provision_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `provision_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision`
--

LOCK TABLES `provision` WRITE;
/*!40000 ALTER TABLE `provision` DISABLE KEYS */;
/*!40000 ALTER TABLE `provision` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `provision_family_ibfk_1` FOREIGN KEY (`provision_id`) REFERENCES `provision` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `provision_family_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision_family`
--

LOCK TABLES `provision_family` WRITE;
/*!40000 ALTER TABLE `provision_family` DISABLE KEYS */;
/*!40000 ALTER TABLE `provision_family` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `provision_update_family_ibfk_1` FOREIGN KEY (`provision_family_id`) REFERENCES `provision_family` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `provision_update_family_ibfk_2` FOREIGN KEY (`osversion_id`) REFERENCES `osversion` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `provision_update_family`
--

LOCK TABLES `provision_update_family` WRITE;
/*!40000 ALTER TABLE `provision_update_family` DISABLE KEYS */;
/*!40000 ALTER TABLE `provision_update_family` ENABLE KEYS */;
UNLOCK TABLES;

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
  `result` enum('New','Pass','Warn','Fail','Panic','None','Skip') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Installing','Running','Reserved','Completed','Cancelled','Aborted') NOT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `_host_requires` text DEFAULT NULL,
  `_distro_requires` text DEFAULT NULL,
  `kickstart` text DEFAULT NULL,
  `type` varchar(30) NOT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  `whiteboard` varchar(4096) DEFAULT NULL,
  `ks_meta` varchar(1024) DEFAULT NULL,
  `kernel_options` varchar(1024) DEFAULT NULL,
  `kernel_options_post` varchar(1024) DEFAULT NULL,
  `role` varchar(255) DEFAULT NULL,
  `panic` varchar(20) DEFAULT NULL,
  `_partitions` text DEFAULT NULL,
  `autopick_random` tinyint(1) NOT NULL,
  `log_server` varchar(255) DEFAULT NULL,
  `virt_status` enum('Possible','Precluded','Succeeded','Skipped','Failed') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_set_id` (`recipe_set_id`),
  KEY `distro_tree_id` (`distro_tree_id`),
  KEY `ix_recipe_status` (`status`),
  KEY `ix_recipe_virt_status` (`virt_status`),
  KEY `ix_recipe_log_server` (`log_server`),
  KEY `ix_recipe_result` (`result`),
  KEY `ix_recipe_start_time` (`start_time`),
  CONSTRAINT `recipe_ibfk_1` FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`),
  CONSTRAINT `recipe_ibfk_2` FOREIGN KEY (`distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`autopick_random` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe`
--

LOCK TABLES `recipe` WRITE;
/*!40000 ALTER TABLE `recipe` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_activity`
--

DROP TABLE IF EXISTS `recipe_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_activity` (
  `id` int(11) NOT NULL,
  `recipe_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_activity_recipe_id_fk` (`recipe_id`),
  CONSTRAINT `recipe_activity_id_fk` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `recipe_activity_recipe_id_fk` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_activity`
--

LOCK TABLES `recipe_activity` WRITE;
/*!40000 ALTER TABLE `recipe_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_ksappend`
--

DROP TABLE IF EXISTS `recipe_ksappend`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_ksappend` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_id` int(11) NOT NULL,
  `ks_append` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_ksappend_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_ksappend`
--

LOCK TABLES `recipe_ksappend` WRITE;
/*!40000 ALTER TABLE `recipe_ksappend` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_ksappend` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_repo`
--

LOCK TABLES `recipe_repo` WRITE;
/*!40000 ALTER TABLE `recipe_repo` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_repo` ENABLE KEYS */;
UNLOCK TABLES;

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
  `when` enum('onabort','onfail','onwarn','always') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  CONSTRAINT `recipe_reservation_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_reservation`
--

LOCK TABLES `recipe_reservation` WRITE;
/*!40000 ALTER TABLE `recipe_reservation` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_reservation` ENABLE KEYS */;
UNLOCK TABLES;

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `recipe_id` (`recipe_id`),
  KEY `ix_recipe_resource_fqdn` (`fqdn`),
  CONSTRAINT `recipe_resource_recipe_id_fk` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_resource`
--

LOCK TABLES `recipe_resource` WRITE;
/*!40000 ALTER TABLE `recipe_resource` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_resource` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_reviewed_state`
--

DROP TABLE IF EXISTS `recipe_reviewed_state`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_reviewed_state` (
  `recipe_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `reviewed` tinyint(1) NOT NULL,
  PRIMARY KEY (`recipe_id`,`user_id`),
  KEY `recipe_reviewed_state_user_id_fk` (`user_id`),
  CONSTRAINT `recipe_reviewed_state_recipe_id_fk` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_reviewed_state_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `CONSTRAINT_1` CHECK (`reviewed` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_reviewed_state`
--

LOCK TABLES `recipe_reviewed_state` WRITE;
/*!40000 ALTER TABLE `recipe_reviewed_state` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_reviewed_state` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `recipe_rpm_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`running_kernel` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_rpm`
--

LOCK TABLES `recipe_rpm` WRITE;
/*!40000 ALTER TABLE `recipe_rpm` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_rpm` ENABLE KEYS */;
UNLOCK TABLES;

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
  `result` enum('New','Pass','Warn','Fail','Panic','None','Skip') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Installing','Running','Reserved','Completed','Cancelled','Aborted') NOT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `ttasks` int(11) DEFAULT NULL,
  `ntasks` int(11) DEFAULT NULL,
  `ptasks` int(11) DEFAULT NULL,
  `wtasks` int(11) DEFAULT NULL,
  `ftasks` int(11) DEFAULT NULL,
  `ktasks` int(11) DEFAULT NULL,
  `waived` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `job_id` (`job_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  KEY `ix_recipe_set_priority` (`priority`),
  KEY `ix_recipe_set_result` (`result`),
  KEY `ix_recipe_set_status` (`status`),
  CONSTRAINT `recipe_set_ibfk_1` FOREIGN KEY (`job_id`) REFERENCES `job` (`id`),
  CONSTRAINT `recipe_set_ibfk_2` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`waived` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_set`
--

LOCK TABLES `recipe_set` WRITE;
/*!40000 ALTER TABLE `recipe_set` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_set` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_set_comment`
--

DROP TABLE IF EXISTS `recipe_set_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_set_comment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_set_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `comment` varchar(4000) NOT NULL,
  `created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_set_id` (`recipe_set_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `recipe_set_comment_ibfk_1` FOREIGN KEY (`recipe_set_id`) REFERENCES `recipe_set` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_set_comment_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_set_comment`
--

LOCK TABLES `recipe_set_comment` WRITE;
/*!40000 ALTER TABLE `recipe_set_comment` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_set_comment` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `recipe_tag` WRITE;
/*!40000 ALTER TABLE `recipe_tag` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_tag` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `recipe_tag_map` WRITE;
/*!40000 ALTER TABLE `recipe_tag_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_tag_map` ENABLE KEYS */;
UNLOCK TABLES;

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
  `fetch_subdir` varchar(2048) NOT NULL,
  `task_id` int(11) DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  `finish_time` datetime DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None','Skip') NOT NULL,
  `status` enum('New','Processed','Queued','Scheduled','Waiting','Installing','Running','Reserved','Completed','Cancelled','Aborted') NOT NULL,
  `role` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_id` (`recipe_id`),
  KEY `task_id` (`task_id`),
  KEY `ix_recipe_task_version` (`version`),
  KEY `ix_recipe_task_name` (`name`),
  KEY `ix_recipe_task_name_version` (`name`,`version`),
  CONSTRAINT `recipe_task_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `recipe_task_ibfk_2` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task`
--

LOCK TABLES `recipe_task` WRITE;
/*!40000 ALTER TABLE `recipe_task` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_task_comment`
--

DROP TABLE IF EXISTS `recipe_task_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_comment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `comment` varchar(4000) NOT NULL,
  `created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_comment_recipe_task_id_fk` (`recipe_task_id`),
  KEY `recipe_task_comment_user_id_fk` (`user_id`),
  CONSTRAINT `recipe_task_comment_recipe_task_id_fk` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_task_comment_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_comment`
--

LOCK TABLES `recipe_task_comment` WRITE;
/*!40000 ALTER TABLE `recipe_task_comment` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task_comment` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_task_param`
--

DROP TABLE IF EXISTS `recipe_task_param`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_param` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `value` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_param_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_param`
--

LOCK TABLES `recipe_task_param` WRITE;
/*!40000 ALTER TABLE `recipe_task_param` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task_param` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_task_result`
--

DROP TABLE IF EXISTS `recipe_task_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_result` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_id` int(11) NOT NULL,
  `path` varchar(2048) DEFAULT NULL,
  `result` enum('New','Pass','Warn','Fail','Panic','None','Skip') NOT NULL,
  `score` decimal(10,0) DEFAULT NULL,
  `log` text DEFAULT NULL,
  `start_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_id` (`recipe_task_id`),
  CONSTRAINT `recipe_task_result_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_result`
--

LOCK TABLES `recipe_task_result` WRITE;
/*!40000 ALTER TABLE `recipe_task_result` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task_result` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipe_task_result_comment`
--

DROP TABLE IF EXISTS `recipe_task_result_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipe_task_result_comment` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `recipe_task_result_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `comment` varchar(4000) NOT NULL,
  `created` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipe_task_result_comment_recipe_task_result_id_fk` (`recipe_task_result_id`),
  KEY `recipe_task_result_comment_user_id_fk` (`user_id`),
  CONSTRAINT `recipe_task_result_comment_recipe_task_result_id_fk` FOREIGN KEY (`recipe_task_result_id`) REFERENCES `recipe_task_result` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `recipe_task_result_comment_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_result_comment`
--

LOCK TABLES `recipe_task_result_comment` WRITE;
/*!40000 ALTER TABLE `recipe_task_result_comment` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task_result_comment` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `recipe_task_rpm_ibfk_1` FOREIGN KEY (`recipe_task_id`) REFERENCES `recipe_task` (`id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`running_kernel` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipe_task_rpm`
--

LOCK TABLES `recipe_task_rpm` WRITE;
/*!40000 ALTER TABLE `recipe_task_rpm` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipe_task_rpm` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `recipeset_activity`
--

DROP TABLE IF EXISTS `recipeset_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `recipeset_activity` (
  `id` int(11) NOT NULL,
  `recipeset_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `recipeset_id` (`recipeset_id`),
  CONSTRAINT `recipeset_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `recipeset_activity_ibfk_2` FOREIGN KEY (`recipeset_id`) REFERENCES `recipe_set` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `recipeset_activity`
--

LOCK TABLES `recipeset_activity` WRITE;
/*!40000 ALTER TABLE `recipeset_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `recipeset_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `rendered_kickstart`
--

DROP TABLE IF EXISTS `rendered_kickstart`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `rendered_kickstart` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `kickstart` mediumtext DEFAULT NULL,
  `url` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `rendered_kickstart`
--

LOCK TABLES `rendered_kickstart` WRITE;
/*!40000 ALTER TABLE `rendered_kickstart` DISABLE KEYS */;
/*!40000 ALTER TABLE `rendered_kickstart` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `reservation`
--

LOCK TABLES `reservation` WRITE;
/*!40000 ALTER TABLE `reservation` DISABLE KEYS */;
/*!40000 ALTER TABLE `reservation` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `retention_tag`
--

DROP TABLE IF EXISTS `retention_tag`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `retention_tag` (
  `id` int(11) NOT NULL,
  `default_` tinyint(1) DEFAULT NULL,
  `expire_in_days` int(11) NOT NULL,
  `needs_product` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `retention_tag_ibfk_1` FOREIGN KEY (`id`) REFERENCES `beaker_tag` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `CONSTRAINT_1` CHECK (`needs_product` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `retention_tag`
--

LOCK TABLES `retention_tag` WRITE;
/*!40000 ALTER TABLE `retention_tag` DISABLE KEYS */;
INSERT INTO `retention_tag` VALUES (1,1,30,0),(2,0,60,0),(3,0,120,0),(4,0,0,1),(5,0,0,1);
/*!40000 ALTER TABLE `retention_tag` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `sshpubkey`
--

LOCK TABLES `sshpubkey` WRITE;
/*!40000 ALTER TABLE `sshpubkey` DISABLE KEYS */;
/*!40000 ALTER TABLE `sshpubkey` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `submission_delegate`
--

LOCK TABLES `submission_delegate` WRITE;
/*!40000 ALTER TABLE `submission_delegate` DISABLE KEYS */;
/*!40000 ALTER TABLE `submission_delegate` ENABLE KEYS */;
UNLOCK TABLES;

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
  `type` enum('Laptop','Machine','Prototype','Resource') NOT NULL,
  `scheduler_status` enum('Idle','Pending','Reserved') NOT NULL,
  `status` enum('Automated','Broken','Manual','Removed') NOT NULL,
  `status_reason` varchar(4000) DEFAULT NULL,
  `memory` int(11) DEFAULT NULL,
  `checksum` varchar(32) DEFAULT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  `mac_address` varchar(18) DEFAULT NULL,
  `loan_id` int(11) DEFAULT NULL,
  `loan_comment` varchar(1000) DEFAULT NULL,
  `release_action` enum('PowerOff','LeaveOn','ReProvision') NOT NULL,
  `reprovision_distro_tree_id` int(11) DEFAULT NULL,
  `hypervisor_id` int(11) DEFAULT NULL,
  `kernel_type_id` int(11) NOT NULL,
  `custom_access_policy_id` int(11) DEFAULT NULL,
  `active_access_policy_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `fqdn` (`fqdn`),
  KEY `owner_id` (`owner_id`),
  KEY `user_id` (`user_id`),
  KEY `lab_controller_id` (`lab_controller_id`),
  KEY `loan_id` (`loan_id`),
  KEY `reprovision_distro_tree_id` (`reprovision_distro_tree_id`),
  KEY `hypervisor_id` (`hypervisor_id`),
  KEY `kernel_type_id` (`kernel_type_id`),
  KEY `custom_access_policy_id_fk` (`custom_access_policy_id`),
  KEY `active_access_policy_id_fk` (`active_access_policy_id`),
  CONSTRAINT `active_access_policy_id_fk` FOREIGN KEY (`active_access_policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `custom_access_policy_id_fk` FOREIGN KEY (`custom_access_policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `system_ibfk_1` FOREIGN KEY (`owner_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_3` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`),
  CONSTRAINT `system_ibfk_4` FOREIGN KEY (`loan_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `system_ibfk_5` FOREIGN KEY (`reprovision_distro_tree_id`) REFERENCES `distro_tree` (`id`),
  CONSTRAINT `system_ibfk_6` FOREIGN KEY (`hypervisor_id`) REFERENCES `hypervisor` (`id`),
  CONSTRAINT `system_ibfk_7` FOREIGN KEY (`kernel_type_id`) REFERENCES `kernel_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system`
--

LOCK TABLES `system` WRITE;
/*!40000 ALTER TABLE `system` DISABLE KEYS */;
/*!40000 ALTER TABLE `system` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `system_access_policy`
--

DROP TABLE IF EXISTS `system_access_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `system_access_policy` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_access_policy`
--

LOCK TABLES `system_access_policy` WRITE;
/*!40000 ALTER TABLE `system_access_policy` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_access_policy` ENABLE KEYS */;
UNLOCK TABLES;

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
  `permission` enum('view','view_power','edit_policy','edit_system','loan_any','loan_self','control_system','reserve') NOT NULL,
  PRIMARY KEY (`id`),
  KEY `system_access_policy_rule_policy_id_fk` (`policy_id`),
  KEY `system_access_policy_rule_user_id_fk` (`user_id`),
  KEY `system_access_policy_rule_group_id_fk` (`group_id`),
  CONSTRAINT `system_access_policy_rule_group_id_fk` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`),
  CONSTRAINT `system_access_policy_rule_policy_id_fk` FOREIGN KEY (`policy_id`) REFERENCES `system_access_policy` (`id`),
  CONSTRAINT `system_access_policy_rule_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_access_policy_rule`
--

LOCK TABLES `system_access_policy_rule` WRITE;
/*!40000 ALTER TABLE `system_access_policy_rule` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_access_policy_rule` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `system_activity_ibfk_1` FOREIGN KEY (`id`) REFERENCES `activity` (`id`),
  CONSTRAINT `system_activity_ibfk_2` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_activity`
--

LOCK TABLES `system_activity` WRITE;
/*!40000 ALTER TABLE `system_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_activity` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `ix_system_arch_map_system_id` (`system_id`),
  KEY `ix_system_arch_map_arch_id` (`arch_id`),
  CONSTRAINT `system_arch_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_arch_map_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_arch_map`
--

LOCK TABLES `system_arch_map` WRITE;
/*!40000 ALTER TABLE `system_arch_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_arch_map` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `system_cc_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_cc`
--

LOCK TABLES `system_cc` WRITE;
/*!40000 ALTER TABLE `system_cc` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_cc` ENABLE KEYS */;
UNLOCK TABLES;

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
  KEY `ix_system_device_map_device_id` (`device_id`),
  KEY `ix_system_device_map_system_id` (`system_id`),
  CONSTRAINT `system_device_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_device_map_ibfk_2` FOREIGN KEY (`device_id`) REFERENCES `device` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_device_map`
--

LOCK TABLES `system_device_map` WRITE;
/*!40000 ALTER TABLE `system_device_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_device_map` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_hardware_scan_recipe_map`
--

LOCK TABLES `system_hardware_scan_recipe_map` WRITE;
/*!40000 ALTER TABLE `system_hardware_scan_recipe_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_hardware_scan_recipe_map` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_pool`
--

LOCK TABLES `system_pool` WRITE;
/*!40000 ALTER TABLE `system_pool` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_pool` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `system_pool_activity` WRITE;
/*!40000 ALTER TABLE `system_pool_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_pool_activity` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `system_pool_map_ibfk_1` FOREIGN KEY (`system_id`) REFERENCES `system` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `system_pool_map_ibfk_2` FOREIGN KEY (`pool_id`) REFERENCES `system_pool` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_pool_map`
--

LOCK TABLES `system_pool_map` WRITE;
/*!40000 ALTER TABLE `system_pool_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_pool_map` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `system_recipe_map` WRITE;
/*!40000 ALTER TABLE `system_recipe_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_recipe_map` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `system_resource` WRITE;
/*!40000 ALTER TABLE `system_resource` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_resource` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `system_status_duration`
--

LOCK TABLES `system_status_duration` WRITE;
/*!40000 ALTER TABLE `system_status_duration` DISABLE KEYS */;
/*!40000 ALTER TABLE `system_status_duration` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task`
--

DROP TABLE IF EXISTS `task`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `rpm` varchar(255) NOT NULL,
  `path` varchar(4096) NOT NULL,
  `description` varchar(2048) NOT NULL,
  `avg_time` int(11) NOT NULL,
  `destructive` tinyint(1) DEFAULT NULL,
  `nda` tinyint(1) DEFAULT NULL,
  `creation_date` datetime NOT NULL,
  `update_date` datetime NOT NULL,
  `uploader_id` int(11) DEFAULT NULL,
  `owner` varchar(255) NOT NULL,
  `version` varchar(256) NOT NULL,
  `license` varchar(256) NOT NULL,
  `priority` varchar(256) DEFAULT NULL,
  `valid` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `rpm` (`rpm`),
  KEY `uploader_id` (`uploader_id`),
  KEY `ix_task_owner` (`owner`),
  CONSTRAINT `task_ibfk_1` FOREIGN KEY (`uploader_id`) REFERENCES `tg_user` (`user_id`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`valid` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task`
--

LOCK TABLES `task` WRITE;
/*!40000 ALTER TABLE `task` DISABLE KEYS */;
/*!40000 ALTER TABLE `task` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_bugzilla`
--

DROP TABLE IF EXISTS `task_bugzilla`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_bugzilla` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `bugzilla_id` int(11) DEFAULT NULL,
  `task_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `task_id` (`task_id`),
  CONSTRAINT `task_bugzilla_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_bugzilla`
--

LOCK TABLES `task_bugzilla` WRITE;
/*!40000 ALTER TABLE `task_bugzilla` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_bugzilla` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_exclude_arch`
--

DROP TABLE IF EXISTS `task_exclude_arch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclude_arch` (
  `task_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`arch_id`),
  KEY `ix_task_exclude_arch_task_id` (`task_id`),
  KEY `ix_task_exclude_arch_arch_id` (`arch_id`),
  CONSTRAINT `task_exclude_arch_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_exclude_arch_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclude_arch`
--

LOCK TABLES `task_exclude_arch` WRITE;
/*!40000 ALTER TABLE `task_exclude_arch` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_exclude_arch` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_exclude_osmajor`
--

DROP TABLE IF EXISTS `task_exclude_osmajor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclude_osmajor` (
  `task_id` int(11) NOT NULL,
  `osmajor_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`osmajor_id`),
  KEY `ix_task_exclude_osmajor_osmajor_id` (`osmajor_id`),
  KEY `ix_task_exclude_osmajor_task_id` (`task_id`),
  CONSTRAINT `task_exclude_osmajor_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_exclude_osmajor_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclude_osmajor`
--

LOCK TABLES `task_exclude_osmajor` WRITE;
/*!40000 ALTER TABLE `task_exclude_osmajor` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_exclude_osmajor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_exclusive_arch`
--

DROP TABLE IF EXISTS `task_exclusive_arch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclusive_arch` (
  `task_id` int(11) NOT NULL,
  `arch_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`arch_id`),
  KEY `ix_task_exclusive_arch_task_id` (`task_id`),
  KEY `ix_task_exclusive_arch_arch_id` (`arch_id`),
  CONSTRAINT `task_exclusive_arch_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_exclusive_arch_ibfk_2` FOREIGN KEY (`arch_id`) REFERENCES `arch` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclusive_arch`
--

LOCK TABLES `task_exclusive_arch` WRITE;
/*!40000 ALTER TABLE `task_exclusive_arch` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_exclusive_arch` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_exclusive_osmajor`
--

DROP TABLE IF EXISTS `task_exclusive_osmajor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_exclusive_osmajor` (
  `task_id` int(11) NOT NULL,
  `osmajor_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`osmajor_id`),
  KEY `ix_task_exclusive_osmajor_task_id` (`task_id`),
  KEY `ix_task_exclusive_osmajor_osmajor_id` (`osmajor_id`),
  CONSTRAINT `task_exclusive_osmajor_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_exclusive_osmajor_ibfk_2` FOREIGN KEY (`osmajor_id`) REFERENCES `osmajor` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_exclusive_osmajor`
--

LOCK TABLES `task_exclusive_osmajor` WRITE;
/*!40000 ALTER TABLE `task_exclusive_osmajor` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_exclusive_osmajor` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_package`
--

DROP TABLE IF EXISTS `task_package`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_package` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `package` varchar(255) COLLATE utf8_bin NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `package` (`package`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_package`
--

LOCK TABLES `task_package` WRITE;
/*!40000 ALTER TABLE `task_package` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_package` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_packages_custom_map`
--

DROP TABLE IF EXISTS `task_packages_custom_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_custom_map` (
  `recipe_id` int(11) NOT NULL,
  `package_id` int(11) NOT NULL,
  PRIMARY KEY (`recipe_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_custom_map_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_custom_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_custom_map`
--

LOCK TABLES `task_packages_custom_map` WRITE;
/*!40000 ALTER TABLE `task_packages_custom_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_packages_custom_map` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_packages_required_map`
--

DROP TABLE IF EXISTS `task_packages_required_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_required_map` (
  `task_id` int(11) NOT NULL,
  `package_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_required_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_required_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_required_map`
--

LOCK TABLES `task_packages_required_map` WRITE;
/*!40000 ALTER TABLE `task_packages_required_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_packages_required_map` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_packages_runfor_map`
--

DROP TABLE IF EXISTS `task_packages_runfor_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_packages_runfor_map` (
  `task_id` int(11) NOT NULL,
  `package_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`package_id`),
  KEY `package_id` (`package_id`),
  CONSTRAINT `task_packages_runfor_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_packages_runfor_map_ibfk_2` FOREIGN KEY (`package_id`) REFERENCES `task_package` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_packages_runfor_map`
--

LOCK TABLES `task_packages_runfor_map` WRITE;
/*!40000 ALTER TABLE `task_packages_runfor_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_packages_runfor_map` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_property_needed`
--

LOCK TABLES `task_property_needed` WRITE;
/*!40000 ALTER TABLE `task_property_needed` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_property_needed` ENABLE KEYS */;
UNLOCK TABLES;

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_type`
--

LOCK TABLES `task_type` WRITE;
/*!40000 ALTER TABLE `task_type` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `task_type_map`
--

DROP TABLE IF EXISTS `task_type_map`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `task_type_map` (
  `task_id` int(11) NOT NULL,
  `task_type_id` int(11) NOT NULL,
  PRIMARY KEY (`task_id`,`task_type_id`),
  KEY `task_type_id` (`task_type_id`),
  CONSTRAINT `task_type_map_ibfk_1` FOREIGN KEY (`task_id`) REFERENCES `task` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `task_type_map_ibfk_2` FOREIGN KEY (`task_type_id`) REFERENCES `task_type` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `task_type_map`
--

LOCK TABLES `task_type_map` WRITE;
/*!40000 ALTER TABLE `task_type_map` DISABLE KEYS */;
/*!40000 ALTER TABLE `task_type_map` ENABLE KEYS */;
UNLOCK TABLES;

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
  `description` varchar(4000) DEFAULT NULL,
  `root_password` varchar(255) DEFAULT NULL,
  `membership_type` enum('normal','ldap','inverted') NOT NULL,
  `created` datetime DEFAULT NULL,
  PRIMARY KEY (`group_id`),
  UNIQUE KEY `group_name` (`group_name`),
  KEY `ix_tg_group_membership_type` (`membership_type`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tg_group`
--

LOCK TABLES `tg_group` WRITE;
/*!40000 ALTER TABLE `tg_group` DISABLE KEYS */;
INSERT INTO `tg_group` VALUES (1,'admin','Admin',NULL,NULL,'normal','2023-12-24 14:34:08'),(2,'lab_controller','Lab Controller',NULL,NULL,'normal','2023-12-24 14:34:08');
/*!40000 ALTER TABLE `tg_group` ENABLE KEYS */;
UNLOCK TABLES;

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
  `password` text DEFAULT NULL,
  `root_password` varchar(255) DEFAULT NULL,
  `rootpw_changed` datetime DEFAULT NULL,
  `openstack_trust_id` varchar(4000) DEFAULT NULL,
  `use_old_job_page` tinyint(1) NOT NULL,
  `notify_job_completion` tinyint(1) NOT NULL,
  `notify_broken_system` tinyint(1) NOT NULL,
  `notify_system_loan` tinyint(1) NOT NULL,
  `notify_group_membership` tinyint(1) NOT NULL,
  `notify_reservesys` tinyint(1) NOT NULL,
  `created` datetime DEFAULT NULL,
  `disabled` tinyint(1) NOT NULL,
  `removed` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_name` (`user_name`),
  KEY `ix_tg_user_email_address` (`email_address`),
  CONSTRAINT `CONSTRAINT_1` CHECK (`use_old_job_page` in (0,1)),
  CONSTRAINT `CONSTRAINT_2` CHECK (`notify_job_completion` in (0,1)),
  CONSTRAINT `CONSTRAINT_3` CHECK (`notify_broken_system` in (0,1)),
  CONSTRAINT `CONSTRAINT_4` CHECK (`notify_system_loan` in (0,1)),
  CONSTRAINT `CONSTRAINT_5` CHECK (`notify_group_membership` in (0,1)),
  CONSTRAINT `CONSTRAINT_6` CHECK (`notify_reservesys` in (0,1)),
  CONSTRAINT `CONSTRAINT_7` CHECK (`disabled` in (0,1))
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `tg_user`
--

LOCK TABLES `tg_user` WRITE;
/*!40000 ALTER TABLE `tg_user` DISABLE KEYS */;
INSERT INTO `tg_user` VALUES (1,'admin','me@example.com',NULL,'$pbkdf2-sha512$25000$Ucp5jzFmLMW49967N8YYww$uJgmYL9FOcj4ovtRe1lS7/nJovRoWFa.Ig2mqsKhrfKOqGEw.HPKqGFcN5BFZxT2D.YQZOmRx.AKyIm12u2GaQ',NULL,NULL,NULL,0,1,1,1,1,1,'2023-12-24 14:34:08',0,NULL);
/*!40000 ALTER TABLE `tg_user` ENABLE KEYS */;
UNLOCK TABLES;

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

LOCK TABLES `user_activity` WRITE;
/*!40000 ALTER TABLE `user_activity` DISABLE KEYS */;
/*!40000 ALTER TABLE `user_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `user_group`
--

DROP TABLE IF EXISTS `user_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `user_group` (
  `user_id` int(11) NOT NULL,
  `group_id` int(11) NOT NULL,
  `is_owner` tinyint(1) NOT NULL,
  PRIMARY KEY (`user_id`,`group_id`),
  KEY `ix_user_group_user_id` (`user_id`),
  KEY `ix_user_group_group_id` (`group_id`),
  CONSTRAINT `user_group_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `tg_user` (`user_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `user_group_ibfk_2` FOREIGN KEY (`group_id`) REFERENCES `tg_group` (`group_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `CONSTRAINT_1` CHECK (`is_owner` in (0,1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_group`
--

LOCK TABLES `user_group` WRITE;
/*!40000 ALTER TABLE `user_group` DISABLE KEYS */;
INSERT INTO `user_group` VALUES (1,1,1);
/*!40000 ALTER TABLE `user_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `virt_resource`
--

DROP TABLE IF EXISTS `virt_resource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `virt_resource` (
  `id` int(11) NOT NULL,
  `instance_id` binary(16) NOT NULL,
  `network_id` binary(16) DEFAULT NULL,
  `subnet_id` binary(16) DEFAULT NULL,
  `router_id` binary(16) DEFAULT NULL,
  `floating_ip` bigint(20) DEFAULT NULL,
  `instance_created` datetime DEFAULT NULL,
  `instance_deleted` datetime DEFAULT NULL,
  `lab_controller_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `virt_resource_lab_controller_id_fk` (`lab_controller_id`),
  CONSTRAINT `virt_resource_id_fk` FOREIGN KEY (`id`) REFERENCES `recipe_resource` (`id`),
  CONSTRAINT `virt_resource_lab_controller_id_fk` FOREIGN KEY (`lab_controller_id`) REFERENCES `lab_controller` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `virt_resource`
--

LOCK TABLES `virt_resource` WRITE;
/*!40000 ALTER TABLE `virt_resource` DISABLE KEYS */;
/*!40000 ALTER TABLE `virt_resource` ENABLE KEYS */;
UNLOCK TABLES;

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
  CONSTRAINT `watchdog_ibfk_1` FOREIGN KEY (`recipe_id`) REFERENCES `recipe` (`id`),
  CONSTRAINT `watchdog_ibfk_2` FOREIGN KEY (`recipetask_id`) REFERENCES `recipe_task` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `watchdog`
--

LOCK TABLES `watchdog` WRITE;
/*!40000 ALTER TABLE `watchdog` DISABLE KEYS */;
/*!40000 ALTER TABLE `watchdog` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2023-12-24 14:41:23
