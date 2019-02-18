-- MySQL dump 10.15  Distrib 10.0.37-MariaDB, for debian-linux-gnueabihf (armv7l)
--
-- Host: localhost    Database: aq_db
-- ------------------------------------------------------
-- Server version	10.0.37-MariaDB-0+deb8u1

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
-- Table structure for table `device_types`
--

DROP TABLE IF EXISTS `device_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `device_types` (
  `device_type` int(11) NOT NULL AUTO_INCREMENT,
  `processor` text,
  `Connection` varchar(8) DEFAULT NULL,
  `particle_sensor` text,
  `temp_sensor` text,
  `power` text,
  `Software` text,
  `Other` text,
  PRIMARY KEY (`device_type`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `devices`
--

DROP TABLE IF EXISTS `devices`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `devices` (
  `device_id` int(11) NOT NULL AUTO_INCREMENT,
  `device_name` varchar(16) NOT NULL,
  `device_type` int(11) NOT NULL,
  `owner_id` int(11) DEFAULT NULL,
  `device_latitude` double DEFAULT NULL,
  `device_longitude` double DEFAULT NULL,
  PRIMARY KEY (`device_id`),
  UNIQUE KEY `device_name_idx` (`device_name`),
  KEY `owner_fk` (`owner_id`),
  KEY `device_type_fk` (`device_type`),
  CONSTRAINT `device_type_fk` FOREIGN KEY (`device_type`) REFERENCES `device_types` (`device_type`),
  CONSTRAINT `owner_fk` FOREIGN KEY (`owner_id`) REFERENCES `owners` (`owner_id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=27 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `owners`
--

DROP TABLE IF EXISTS `owners`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `owners` (
  `owner_id` int(11) NOT NULL AUTO_INCREMENT,
  `fname` text,
  `lname` text,
  `postcode` varchar(16) DEFAULT NULL,
  `phone` varchar(16) DEFAULT NULL,
  `email` text,
  PRIMARY KEY (`owner_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reading_value_types`
--

DROP TABLE IF EXISTS `reading_value_types`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reading_value_types` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `short_descr` varchar(16) NOT NULL DEFAULT '',
  `friendly_text` varchar(45) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `reading_values`
--

DROP TABLE IF EXISTS `reading_values`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `reading_values` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `reading_id` int(11) NOT NULL,
  `value` double NOT NULL,
  `reading_value_types_id` int(11) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `reading_values_readings_idx` (`reading_id`),
  KEY `fk_types_id` (`reading_value_types_id`),
  CONSTRAINT `fk_types_id` FOREIGN KEY (`reading_value_types_id`) REFERENCES `reading_value_types` (`id`),
  CONSTRAINT `reading_values_readings` FOREIGN KEY (`reading_id`) REFERENCES `readings` (`id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=426344 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `readings`
--

DROP TABLE IF EXISTS `readings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `readings` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `storedon` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `recordedon` timestamp NULL DEFAULT NULL,
  `device_id` int(11) NOT NULL,
  `raw_json` text,
  `reading_latitude` double DEFAULT NULL,
  `reading_longitude` double DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `device_id` (`device_id`),
  CONSTRAINT `device_fk` FOREIGN KEY (`device_id`) REFERENCES `devices` (`device_id`) ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=65886 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2019-02-18 12:05:39
