#!/usr/bin/python3
"""
DevChecker V3.00.py

utility to update the "devices.visible" flag to hide a sensor based on daysSinceLastSeen. Typically 31 days allowed
in case the owner has taken the sensor down for a rebuild

if a device comes back on line the flag is reset automatically by dbLoader.

normally runs at midnight using a systemd timer

Version set to V3.00 to signify uses TOML

Author: Brian Norman 1/4/2021
Version: 3.00
"""

import mysql.connector
import logging
import os
import toml
import sys

VERSION="3.00"

print("running on python ",sys.version[0])

# config file names
sharedFile="Shared.toml"
configFile="DevChecker.toml"

try:
	config = toml.load(configFile)
	shared = toml.load(sharedFile)

	debug = config["debug"]["settings"]["debug"]

	if debug:
		logFile = config["debug"]["settings"]["logfile"]
		pidFile = config["debug"]["settings"]["pidfile"]
	else:
		logFile = config["settings"]["logfile"]
		pidFile = config["settings"]["pidfile"]

	daysSinceLastSeen = config["settings"]["daysSinceLastSeen"]

	# logging
	logging.basicConfig(filename=logFile, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logging.DEBUG)
	logging.info("############################### ")
	logging.info(f"Starting device checker Vsn: {VERSION}")

	logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

	# database
	dbHost=shared["database"]["host"]
	dbUser=shared["database"]["user"]
	dbPassword=shared["database"]["passwd"]
	dbName=shared["database"]["dbname"]


	# DevChecker


except KeyError as e:
	errMsg = f"Config file entry missing: {e}"
	if logFile is not None:
		logging.exception(errMsg)
	sys.exit(errMsg)

except Exception as e:
	errMsg = (f"Unable to load settings from config file. Error was {e}")
	if logFile is not None:
		logging.exception(errMsg)
	sys.exit(errMsg)

logging.info("Settings loaded ok")

# create PID file for monitoring
try:
	pid_file = open(pidFile, "w")
	pid_file.write(str(os.getpid()))
	pid_file.close()
except Exception as e:
	# this is not fatal
	logging.error(f"Error writing to {pidFile} error {e}")


###################################
#
# updateVisibility()
#
# sets/resets visible flag based on daysSinceLastSeen
# dbLoader will set this to true when data is next seen
#
#
def updateVisibility():
	global mydb,daysSinceLastSeen
	logging.info("updateVisibility(): Starting")
	try:
		SQL=f"update devices set visible=IF(datediff(now(),last_seen)>={daysSinceLastSeen},0,1)"
		mycursor=mydb.cursor()
		mycursor.execute(SQL)
		mydb.commit()
		logging.info("updateVisibility(): finished ok")
	except Exception as e:
		logging.exception(f"updateVisibility(): Error {e}")

###################################
#
# connectToDatabase()
#
# attempt to connect to the database
# return True on success else False
#
def connectToDatabase():
	global mydb
	# open a database connection
	try:
		mydb = mysql.connector.connect(
			host=dbHost,
			user=dbUser,
			passwd=dbPassword,
			database=dbName
		)

		logging.info("connectToDatabase(): Opened a database connection ok.")
		return True

	except Exception as e:
		errMsg=f"connectToDatabase(): Error {e}"
		logging.exception(errMsg)
		return sys.exit(errMsg)


#############################################################################
#
# main
#
#############################################################################

logging.info("#### DevChecker starting ####")

connectToDatabase() # no return if fails
updateVisibility()
