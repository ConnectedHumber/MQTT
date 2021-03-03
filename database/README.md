# AQ_DB

all things pertaining to the database like schema and a MySql (MariaDB) sqldump (nodata)

NOTE: This is for V2 of the database structure - changes were made to reading_values and reading_value_types to reduce database record sizes

# WARNING
mysqldumps from the server contain generated columns which are STORED - there are only two. One in the devices table and one in the readings table.

If you intend to install the database on a Raspberry Pi you may need to edit the aq_db_nodata.sql file and change STORED to PERSISTENT.
