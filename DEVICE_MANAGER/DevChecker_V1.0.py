#------------------------------------------
#
# DevChecker.py
#
# utility to update the visibile flag based on
# daysSinceLastSeen
#
# if a device comes back on line the flag is reset
# automatically.
#
#
# Author: Brian Norman 2/5/2020
# Version: 1.0
#----------------------------------------------------------------------
Version=1.0

import mysql.connector
import logging
from settings import *

daysSinceLastSeen="31"	# STRING!

logging.basicConfig(filename="/var/log/deviceVisibility.log",format='%(asctime)s %(message)s', level=logging.DEBUG)

###################################
#
# updateVisibility()
#
# sets/resets visible flag based on daysSinceLastSeen
#
#
def updateVisibility():
	global mydb,daysSinceLastSeen
	logging.info("setVisibility(): Starting")
	try:
		SQL="update devices set visible=IF(datediff(now(),last_seen)>="+daysSinceLastSeen+",0,1)"
		mycursor=mydb.cursor()
		mycursor.execute(SQL)
		mydb.commit()
		logging.info("restoreVisibility(): finished ok")
	except Exception as e:
		logging.error("restoreVisibility(): Error %s",e)

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
		logging.error("connectToDatabase(): Error %s",e)
		return False


#############################################################################
#
# main
#
#############################################################################

logging.info("#### DevChecker starting ####")

if not connectToDatabase():
	logging.error("Unable to connect to database to update device visible status")
	exit()



updateVisibility()
