#!/usr/bin/python3
"""
dbLoader.py

Authors: Brian Norman
Date: 22nd March 2021
Version: 3.00
Python Ver: 3

This program receives MQTT messages with a JSON payload from a broker. Messages are added to a queue of jobs
and processed sequentially in the main thread.

The JSON keys MUST include a "dev" which is the unique device identifer. If it is missing or unknown
the message is ignored

"timestamp" is optional but should be the timestamp for the readings.

Other valid keys are listed in the reading_value_types database table which is read when this program starts. If new types are added
this program should be restarted (systemctl restart dbLoader)

There are two possible timestamps in the database. The one sent with the JSON is the date/time when the message was 'recorded on'
by the device. The second is the date/time the data was 'stored on' (into the database) The Sensors Map
https://sensors.connectedhumber.org/app/ uses these timestamps to display data.

configuration information is in dbLoader.toml and Shared.toml

See changelog.md for changes
"""


import sys
import paho.mqtt.client as paho
from dateutil.parser import *
import pytz
from datetime import datetime
import mysql.connector
import time
import json
import logging
import os
import toml

if int(sys.version[0])>=3:
	import queue
else:
	import Queue as queue


VERSION="3.00"	# used for logging
print("running on python ",sys.version[0])

# define the config files
configFile="dbLoader.toml"
sharedFile="Shared.toml"

# get config info
try:
	config=toml.load(configFile)
	shared=toml.load(sharedFile)

	debug=config["debug"]["settings"]["debug"]

	if debug:
		logFile = config["debug"]["settings"]["logfile"]
		pidFile = config["debug"]["settings"]["pidfile"]
	else:
		logFile = config["settings"]["logfile"]
		pidFile = config["settings"]["pidfile"]

	# logging
	logging.basicConfig(filename=logFile, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logging.DEBUG)
	logging.info("############################### ")
	logging.info(f"Starting dbLoader Vsn: {VERSION}")

	logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

	# mqtt
	mqttTopic = shared["mqtt"]["topic"]
	mqttClientUser = shared["mqtt"]["user"]
	mqttClientPassword = shared["mqtt"]["passwd"]
	mqttBroker = shared["mqtt"]["host"]
	mqttKeepAlive = shared["mqtt"]["keepAlive"]
	mqttConnectTimeout = shared["mqtt"]["connectTimeout"]
	# database
	dbHost = shared["database"]["host"]
	dbUser = shared["database"]["user"]
	dbPassword = shared["database"]["passwd"]
	dbName = shared["database"]["dbname"]


	GNSS_Aliases = config["GNSS_Aliases"]

	MAX_JOBS = config["settings"]["max_jobs"]
	MAX_MESSAGE_NUMBER = config["settings"]["max_message_number"]
	type_aliases = config["reading_value_types_aliases"]

except KeyError as e:
	sys.exit(f"logfile entry missing:{e}")
	
except Exception as e:
	sys.exit(f"Unable to load settings from configFile error was {e}")

logging.info("Settings loaded ok")



# create PID file for monitoring
try:
	pid_file = open(pidFile, "w")
	pid_file.write(str(os.getpid()))
	pid_file.close()
except Exception as e:
	# this is not fatal
	logging.error(f"Error writing to {pidFile}, Error: {e}")

if debug:
	sys.exit()
	




mydb=None				# global variable required
message_number=0		# for trackinmg log messages for each on_message
brokerConnected=False
mqttc=None
types_id={}				# populated from the database, manually restart service if changes

# circular buffer (FIFO) for on_message callbacks to process
job_queue=queue.Queue(MAX_JOBS)

thisScript=os.path.basename(__file__)

print("Starting to run ",thisScript,VERSION)		# useful for when the task is first started
logging.info("#############################")	# make it easy to see the restart
logging.info("%s Version %s begins",thisScript,VERSION)

def dbUpdate(msg_num,sql, vals):
	global mydb

	logging.info("dbUpdate(%s): SQL=%s vals=%s",msg_num,sql,str(vals))
	last_insert_id=None
	try:
		# execute SQL to insert a row
		mycursor=mydb.cursor()
		mycursor.execute(sql, vals) # add sql to return last_insert_id()
		# commit the change
		mydb.commit()
		mycursor.execute("select last_insert_id()")
		last_insert_id=mycursor.fetchone()[0]	# return last_insert_id
		return last_insert_id
	except Exception as e:
		logging.exception("dbUpdate(): failed to insert record.")
		return None

#
######################################
#
# decodeJSON
# returns True/False
def decodeJSON(msg_num,payload):
	global payloadJson
	logging.info("process_msg(%s): payload=%s", msg_num, payload)

	try:
		# payload strung was UTF-8 decoded when added to the job queue
		payloadJson = json.loads(payload)
		logging.info("decodeJSON(%s): JSON was read ok", msg_num)
		return True
	except Exception as e:
		logging.exception("decodeJSON(%s): Malformed JSON. message ignored",msg_num)
		return False

#####################################

def getTypeIds(msg_num):
	global mydb,types_id
	# first get the device_id from the device_name by looking it up in the database

	try:
		# SQL SELECT to find device_id
		sql = "SELECT short_descr,id FROM reading_value_types"


		# execute SQL to return one record or None
		mycursor=mydb.cursor()
		mycursor.execute(sql)
		types = mycursor.fetchall()
		for row in types:
			types_id[row[0]]=row[1]

		# add any extra aliases
		for entry in type_aliases.keys():
			types_id[entry]=types_id[type_aliases[entry]]

		return True

	except mysql.connector.InterfaceError:
		logging.exception("getTypeId(%s): Unable to connect to database.", msg_num);
		return None

#####################################

def getDeviceId(msg_num):
	global mydb
	# first get the device_id from the device_name by looking it up in the database

	try:
		device_name = payloadJson['dev']
		# SQL SELECT to find device_id
		sql = "SELECT device_id FROM devices WHERE device_name = %s"
		vals = (device_name,)

		# execute SQL to return one record or None
		mycursor=mydb.cursor()
		mycursor.execute(sql, vals)
		rec = mycursor.fetchone()

		# don't go on if the device_name is not known
		if rec is None:
			logging.error("getDeviceId(%s): device_id not found  name=%s.", msg_num,device_name)
			return None

		# get the device_id from the record
		device_id = rec[0]  # rec is a tuple
		logging.info("process_msg(%s): device_id=%s", msg_num, str(device_id))
		return device_id

	except mysql.connector.InterfaceError:
		logging.exception("process_msg(%s): Unable to connect to database. Insertion skipped", msg_num);
		return None

########################################
#
# getTimeWithTz(timeString)
#
# if timeString does not include timezone information
# adds a UTC timezone
#

def getTimeWithTz(msg_num,timeString):
	try:
		d=parse(timeString)
		if d.tzinfo: return d;

		return d.replace(tzinfo=pytz.utc)

	except Exception as e:
		logging.exception("getTimeWithTz(%s) failed. Timestamp will be ignored.",msg_num)
		return None

#####################################
#
# isValidDate(timestamp)
# checks that timestamp is not in the
# future
#
# returns a timestamp string
# or None (for db insertion)
#####################################

def isValidDate(msg_num,timestamp):

	logging.info("isValidDate(%s): checking timestamp %s",msg_num,timestamp)

	try:
		# get the current time and timestamp in YYYY-MM-DDTHH:MM:SS+nnnn format
		#
		now = getTimeWithTz(msg_num,datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z"))
		ts = getTimeWithTz(msg_num,timestamp)

		# is timestamp in the future?
		if ts>now:
			logging.info("isFutureDate(%s) : %s is a future date. Ignored.",msg_num,timestamp)
			return None

		logging.info("isFutureDate(%s) : %s is a valid date.", msg_num, timestamp)
		# lose the timezone offset
		return ts.strftime('%Y-%m-%d %H:%M:%S')

	except ValueError:

		logging.info("isFutureDate(%s) : Cannot convert timestamp. Check the format is YYYY-MM-DDThh:mm:ss+nnnn. "
					 "Ignored", msg_num, timestamp)
		return None


#
# getRecordedOn()
#
# if the payload contains a timestamp then return it otherwise return None
# to simplify the SQL required
#
def getRecordedOn(msg_num):
	global payloadJson

	if not 'timestamp' in payloadJson:
		logging.info("getRecordedOn(%s): JSON does not contain a timestamp",msg_num)
		return  None

	dateTimeString = payloadJson['timestamp']
	logging.info("getRecordedOn(%s): JSON includes a timestamp %s", msg_num, str(dateTimeString))

	try:
		# recordedONString is a string in the required database format
		recordedOnString = isValidDate(msg_num,dateTimeString)
		logging.info("getRecordedOn(%s): recordedOnString=%s", msg_num, recordedOnString)
		return recordedOnString
	except ValueError:
		logging.exception("process_msg(%s): cannot convert timestamp to datetime object", str(msg_num))
		return None

######################################
#
# addReadingValues()
#
# add allowed data values to the reading_values table

def addReadingValues(msg_num,reading_id):
	global payloadJson,types_id

	logging.info("addReadingValues(%s): trying to add records to reading_values for reading_id=%s", msg_num,
				 str(reading_id))

	# next insert each parameter's reading into reading_values
	sql = "INSERT INTO reading_values (reading_id, value, reading_value_types_id) VALUES (%s, %s, %s)"

	# process the JSON string
	try:
		for key, value in payloadJson.items():

			logging.info("addReadingValues(%s): trying to add record to reading_values for key=%s", msg_num, str(key))
			if not key in types_id:
				logging.info("addReadingValues(%s): Ignoring non-data value key %s found in JSON", msg_num, str(key))
				continue

			logging.info("addReadingValues(%s): processing data value key %s", msg_num, str(key))

			# get the type id from the dictionary
			type_id = types_id[key]
			logging.info("addReadingValues(%s): got reading_value_types_id %s", msg_num, str(type_id))

			# add the new value
			vals = (reading_id, value, type_id)

			if dbUpdate(msg_num,sql, vals) is None:
				logging.error("addReadingValues(%s): failed to insert new record for %s into reading_values table", msg_num,
							  str(key))
			else:
				logging.info("addReadingValues(%s): finished adding data value for key %s", msg_num, str(key))

	except Exception as e:
		logging.exception("addReadingValues(%s): error adding reading_values", msg_num)
		return

	logging.info("addReadingValues(%s): finished adding to reading_values", msg_num)

#####################################
#
# getLatLonAlt()
#
# returns tuple (lat,lon,alt) as strings which can be passed to
# the SQL commands NULL is used so that complesx SQL selection is not needed
#
def getLatLonAlt(msg_num):
	global GNSS_Aliases

	latitude=None
	longitude=None
	altitude=None

	for k in GNSS_Aliases.keys():
		if k in payloadJson:
			if GNSS_Aliases[k]=="longitude":
				longitude=str(payloadJson[k])
			elif GNSS_Aliases[k]=="latitude":
				latitude=str(payloadJson[k])
			elif GNSS_Aliases[k]=="altitude":
				altitude=str(payloadJson[k])

	if latitude is None or longitude is None or altitude is None:
		logging.info("getLatLonAlt(%s): Incomplete GNSS data or none. Ignored.",msg_num)
		return (None,None,None)
	else:
		logging.info("getLatLonAlt(%s): Full GNSS data is included", msg_num)
		return(latitude,longitude,altitude)

#####################################
#
# updateLastSeen(device_id,readings_id)
#
# updates the lastseen column in devices table
# to speed up API interface
#
#####################################

def updateLastSeen(msg_num,device_id,readings_id):
	global mydb
	logging.info("updateLastSeen(%s) device_id=%s,readings_id=%s",msg_num,device_id,readings_id)
	# read back from the database
	SQL="select max(s_or_r) from readings where id=%s"
	mycursor=mydb.cursor()
	mycursor.execute(SQL,[readings_id])
	r=mycursor.fetchone()
	if r is None:
		logging.error("updateLastSeen(%s): unable to get last seen for readings.id=%s", msg_num,readings_id)
		return

	try:
		lastSeen=None
		# update the devices table
		lastSeen=r[0]
		logging.info("updateLastSeen(%s): lastseen=%s",msg_num,lastSeen)
		SQL="update devices set last_seen=%s, visible=1 where device_id=%s"
		mycursor.execute(SQL,[lastSeen,device_id])
		mydb.commit()
		logging.info("updateLastSeen(%s): completed normally",msg_num)
	except Exception as e:
		logging.exception("updateLastSeen(%s): %s",msg_num,e)

#####################################
#
# process_job()
#
# main flow analysing the payload and acting on it
#
# This is called from the main loop when it finds a job
# to do
#
def process_job(msg_num, payload):
	global debug,mydb, payloadJson

	if debug:
		logging.debug(f"process_job({msg_num}) payload={payload}")
		return

	logging.info("-"*40)	# visual separator for the log file
	if not decodeJSON(msg_num,payload):
		return

	# check device id is valid
	device_id=getDeviceId(msg_num)
	if device_id is None:
		logging.error(f"process_job({msg_num}): Unresolved device_id. Payload skipped")
		return

	# GNNS data? if not (None,None,None) is returned for each
	(lat,lon,alt)=getLatLonAlt(msg_num)

	# timestamp provided? if not None is returned
	recordedOn=getRecordedOn(msg_num)

	sql = "INSERT INTO readings (storedon,recordedon,device_id,raw_json,reading_latitude,reading_longitude," \
		  "reading_altitude) values (now(),%s,%s,%s,%s,%s,%s)"

	vals = (recordedOn,device_id, str(payloadJson),lat,lon,alt	)

	readings_id=dbUpdate(msg_num,sql, vals)

	if readings_id is None:
		logging.error("process_job(%s) insert record into readings table failed.",msg_num)
		return

	logging.info("process_job(%s): readings_id=%s",msg_num,str(readings_id))
	logging.info("process_job(%s): parameters=%s",msg_num,str(payloadJson))

	addReadingValues(msg_num,readings_id)

	updateLastSeen(msg_num,device_id,readings_id)

	logging.info("process_job(%s): finished normally",msg_num)

#####################################
#
# on_conenct() callback from MQTT broker
#
def on_connect(mqttc, obj, flags, rc):
	global brokerConnected

	if rc==0:
		brokerConnected=True
		logging.info("on_connect(): callback ok, subscribing to Topic: %s",mqttTopic)
		mqttc.subscribe(mqttTopic, 0)
	else:
		brokerConnected=False
		logging.info("on_connect(): callback error rc=%s",str(rc))

def on_disconnect(client, userdata, rc):
   global brokerConnected
   brokerConnected = False

################################
#
# on_message() MQTT broker callback
#
# UTF-8 decode the payload and add it to the job queue see main()
#
def on_message(mqttc, obj, msg):
	logging.info("on_message() received payload=%s",msg.payload)
	job_queue.put(msg.payload.decode("UTF-8"))

################################
#
# on_subscribe(0 MQTT Broker callback
#
# information only
#
def on_subscribe(mqttc,obj,mid,granted_qos):
	global logging
	logging.info("on_subscribe(): Subscribed with mid=%s",str(mid))


################################
#
# connectToBroker
#
# on_connect sets a global flag brokerConnected
def connectToBroker():
	global mqttc,brokerConnected

	brokerConnected=False

	logging.info("connectTobroker(): Trying to connect to the MQTT broker")
	print("connectToBroker():Trying to connect to the MQTT broker")

	mqttc = paho.Client()  # uses a random client id

	mqttc.on_connect = on_connect
	mqttc.on_subscribe = on_subscribe
	mqttc.on_message = on_message
	mqttc.on_disconnect = on_disconnect

	# use authentication?
	if mqttClientUser is not None:
		logging.info("using MQTT authentication")
		mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
	else:
		logging.info("not using MQTT autentication")

	# terminate if the connection takes too long
	# on_connect sets a global flag brokerConnected
	startConnect = time.time()
	mqttc.loop_start()	# runs in the background, reconnects if needed
	mqttc.connect(mqttBroker, keepalive=mqttKeepAlive)

	while not brokerConnected:
		if (time.time() - startConnect) > mqttConnectTimeout:
			logging.error("broker on_connect time out (%ss)", mqttConnectTimeout)
			return False

	logging.info("Connected to MQTT broker after %s s", int(time.time() - startConnect))
	return True

###################################
#
# connectToDatabase()
#
# attempt to connect to the database
# return True on success else False
#
def connectToDatabase():
	global mydb,dbHost,dbUser,dbPassword,dbName
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
		logging.exception("main(): Unable to connect to the database check Config.toml")
		return False


#############################################################################
#
# main
#
#############################################################################


if not connectToDatabase():
	mqttc.loop_stop()
	sys.exit()

getTypeIds(0)	# if the database changes manually restart the dbLoader service

if not connectToBroker():
	mqttc.loop_stop()
	sys.exit()

# main loop which retrieves jobs from the job_queue
# and passes them to process_job()

while True:
	if not brokerConnected:
		logging.info("Attempting to reconnect to broker")
		if not connectToBroker():
			logging.info("main: unable to re-connect to broker")
			mqttc.loop_stop()
			sys.exit() # systemd will restart us

	# anything to do?
	if not job_queue.empty():
		# make sure the dabase is alive and well
		mydb.ping(reconnect=True, attempts=5, delay=1)
		# TODO add code to check if the connection is really up
		# retrieve the next job and process it
		payload=job_queue.get()	# retrieve the next job
		process_job(message_number,payload)
		# bump the message number with wrap around
		message_number=(message_number+1) % MAX_MESSAGE_NUMBER
	else:

		time.sleep(0.1)
