-- MariaDB dump 10.18  Distrib 10.4.17-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: aq_db
-- ------------------------------------------------------
-- Server version	10.4.17-MariaDB-1:10.4.17+maria~focal

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table "device_class"
--

DROP TABLE IF EXISTS "device_class";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "device_class" (
  "id" int(11) NOT NULL AUTO_INCREMENT,
  "description" varchar(100) DEFAULT NULL,
  PRIMARY KEY ("id")
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "device_sensors"
--

DROP TABLE IF EXISTS "device_sensors";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "device_sensors" (
  "device_id" int(11) NOT NULL,
  "sensors_id" int(11) NOT NULL,
  KEY "fk_device" ("device_id"),
  CONSTRAINT "fk_device" FOREIGN KEY ("device_id") REFERENCES "devices" ("device_id") ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "device_types"
--

DROP TABLE IF EXISTS "device_types";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "device_types" (
  "device_type" int(11) NOT NULL AUTO_INCREMENT,
  "processor" text DEFAULT NULL,
  "Connection" varchar(8) DEFAULT NULL,
  "particle_sensor" text DEFAULT NULL,
  "temp_sensor" text DEFAULT NULL,
  "power" text DEFAULT NULL,
  "Software" text DEFAULT NULL,
  "Other" text DEFAULT NULL,
  PRIMARY KEY ("device_type")
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "devices"
--

DROP TABLE IF EXISTS "devices";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "devices" (
  "device_id" int(11) NOT NULL AUTO_INCREMENT,
  "device_name" varchar(16) NOT NULL,
  "device_type" int(11) NOT NULL,
  "owner_id" int(11) DEFAULT NULL,
  "device_latitude" double DEFAULT 53.725383,
  "device_longitude" double DEFAULT -0.336571,
  "device_altitude" double DEFAULT NULL,
  "lat_lon" geometry GENERATED ALWAYS AS (point("device_latitude","device_longitude")) STORED,
  "visible" tinyint(1) DEFAULT 1,
  "class" int(11) DEFAULT 1,
  "last_seen" timestamp NULL DEFAULT NULL,
  PRIMARY KEY ("device_id"),
  UNIQUE KEY "device_name_idx" ("device_name"),
  KEY "owner_fk" ("owner_id"),
  KEY "device_type_fk" ("device_type"),
  KEY "lat_lon_idx" ("lat_lon"(25)),
  KEY "fk_class" ("class"),
  CONSTRAINT "device_type_fk" FOREIGN KEY ("device_type") REFERENCES "device_types" ("device_type"),
  CONSTRAINT "fk_class" FOREIGN KEY ("class") REFERENCES "device_class" ("id"),
  CONSTRAINT "owner_fk" FOREIGN KEY ("owner_id") REFERENCES "owners" ("owner_id") ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=60 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "owners"
--

DROP TABLE IF EXISTS "owners";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "owners" (
  "owner_id" int(11) NOT NULL AUTO_INCREMENT,
  "fname" text DEFAULT NULL,
  "lname" text DEFAULT NULL,
  "postcode" varchar(16) DEFAULT NULL,
  "phone" varchar(16) DEFAULT NULL,
  "email" text DEFAULT NULL,
  PRIMARY KEY ("owner_id")
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "reading_value_types"
--

DROP TABLE IF EXISTS "reading_value_types";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "reading_value_types" (
  "short_descr" varchar(16) NOT NULL DEFAULT '',
  "friendly_text" varchar(45) DEFAULT NULL,
  "id" int(11) NOT NULL AUTO_INCREMENT,
  PRIMARY KEY ("id")
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "reading_values"
--

DROP TABLE IF EXISTS "reading_values";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "reading_values" (
  "id" int(11) NOT NULL AUTO_INCREMENT,
  "reading_id" int(11) NOT NULL,
  "value" double NOT NULL,
  "reading_value_types_id" int(11) NOT NULL,
  PRIMARY KEY ("id"),
  KEY "reading_values_readings_idx" ("reading_id"),
  KEY "reading_value_types_id" ("reading_value_types_id"),
  CONSTRAINT "fk_readings" FOREIGN KEY ("reading_id") REFERENCES "readings" ("id") ON DELETE CASCADE,
  CONSTRAINT "reading_value_types_id" FOREIGN KEY ("reading_value_types_id") REFERENCES "reading_value_types" ("id") ON DELETE NO ACTION ON UPDATE NO ACTION
) ENGINE=InnoDB AUTO_INCREMENT=8906726 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "readings"
--

DROP TABLE IF EXISTS "readings";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "readings" (
  "id" int(11) NOT NULL AUTO_INCREMENT,
  "storedon" timestamp NOT NULL DEFAULT current_timestamp(),
  "recordedon" timestamp NULL DEFAULT NULL,
  "device_id" int(11) NOT NULL,
  "raw_json" text DEFAULT NULL,
  "reading_latitude" double DEFAULT NULL,
  "reading_longitude" double DEFAULT NULL,
  "reading_altitude" double DEFAULT NULL,
  "s_or_r" timestamp GENERATED ALWAYS AS (coalesce("recordedon","storedon")) STORED,
  PRIMARY KEY ("id"),
  KEY "device_id" ("device_id"),
  KEY "storedon_idx" ("storedon"),
  KEY "recordedon_idx" ("recordedon"),
  KEY "s_or_r_idx" ("s_or_r"),
  CONSTRAINT "fk_devices" FOREIGN KEY ("device_id") REFERENCES "devices" ("device_id") ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2148401 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "sensor_reading_value_types"
--

DROP TABLE IF EXISTS "sensor_reading_value_types";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "sensor_reading_value_types" (
  "id" int(11) NOT NULL AUTO_INCREMENT,
  "sensor_id" int(11) NOT NULL,
  "reading_value_types_id" int(11) NOT NULL,
  PRIMARY KEY ("id"),
  KEY "sensor_fk" ("sensor_id"),
  KEY "reading_value_types_fk" ("reading_value_types_id"),
  CONSTRAINT "reading_value_types_fk" FOREIGN KEY ("reading_value_types_id") REFERENCES "reading_value_types" ("id"),
  CONSTRAINT "sensor_fk" FOREIGN KEY ("sensor_id") REFERENCES "sensors" ("id")
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table "sensors"
--

DROP TABLE IF EXISTS "sensors";
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE IF NOT EXISTS "sensors" (
  "id" int(11) NOT NULL AUTO_INCREMENT,
  "Type" varchar(20) NOT NULL,
  "Description" varchar(255) NOT NULL,
  PRIMARY KEY ("id"),
  UNIQUE KEY "Type_constraint" ("Type")
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping routines for database 'aq_db'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2021-02-04  0:00:02
