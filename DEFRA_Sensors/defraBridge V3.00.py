#!/usr/bin/python3
"""
defraBridge V3.00.py

Downloads DEFRA sensor data and sends it to the MQTT broker for adding to the sensor database.

This code is a modification of example code written by Ben Simmons

Data from all listed sensors is collected into a nested dict before being sorted and sent to the MQTT broker.
This allows all readings produced at the same timestamp to be grouped as one message. The messages are sent
to the MQTT broker in ascending timestamp order so that the database "devices.last_seen" column always reflects the
latest readings.

Runs from a systemd timer, typically 30 minutes past the hour because DEFRA sites update on an hourly basis
but the data may not be available at the top of the hour. At times the data isn't available till
some considerable time later - notably at weekends. Missing data usually have a sensor value of -99.
This code ignores those readings - they should be picked up on later runs.

Install as defraBridge.py or create a symbolic link to this code

Defra device settings are in defraBridge.toml shared settings are in Shared.toml

Note that if the device does not exist in the database mqtt messages will be ignored. Also, if the message 
contains a sensor type which is not listed in the database, e.g. NOX, the reading will be ignored.

Author: Brian N Norman
Date: 1/4/2021
Version: 3.00

"""
import requests
from datetime import datetime, timezone, timedelta
import collections
import logging
import mysql.connector
import paho.mqtt.client as paho
import sys
import time
import json
import os
import toml

VERSION="3.00"
print("running on python ",sys.version[0])

# get config values and check they exist

sharedFile="Shared.toml"
configFile="defraBridge.toml"

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
	logging.basicConfig(filename=logFile,format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s',level=logging.DEBUG)
	logging.info("############################### ")
	logging.info(f"Starting DEFRA sensor data collector Vsn: {VERSION}")

	logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

	# mqtt - from Shared.toml
	mqttTopic=shared["mqtt"]["topic"]
	mqttClientUser=shared["mqtt"]["user"]
	mqttClientPassword = shared["mqtt"]["passwd"]
	mqttBroker=shared["mqtt"]["host"]

	# database
	dbHost=shared["database"]["host"]
	dbUser=shared["database"]["user"]
	dbPassword=shared["database"]["passwd"]
	dbName=shared["database"]["dbname"]

	# defraBridge
	main_url=config["settings"]["main_url"]
	append_url=config["settings"]["append_url"]
	never_seen=config["settings"]["never_seen"]
	stations=config["stations"]

except KeyError as e:
	errMsg=f"Config file entry missing: {e}"
	if logFile is not None:
		logging.exception(errMsg)
	sys.exit(errMsg)
	
except Exception as e:
	errMsg=(f"Unable to load settings from config file. Error was {e}")
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
	logging.exception(f"Non-Fatal error writing to {pidFile}, error was {e}. ignored")

# code after this point should not require changing

mqttc = paho.Client()
lastSeen={} # updated from the database devices table

try:
	mydb= mysql.connector.connect(
				host=dbHost,
				user=dbUser,
				passwd=dbPassword,
				database=dbName
			)
	logging.info("Database connection ok")

except Exception as e:
	errMsg=f"Database connection failed error={e}"
	logging.exception(errMsg)
	sys.exit(errMsg)

########################################################################

lastSeen={} # cache for last seen timestamps to reduce database queries

def getLastSeen(station):
	"""
	get last seen for the given station (device name)
	:return: datetime last seen data from this station
	"""

	global lastSeen,mydb,device_id,logging

	if station in lastSeen.keys():
		logging.info(f"Using cached lastSeen station={station} timestamp={lastSeen[station]}")
		return lastSeen[station]

	sql = f"select last_seen from devices where device_name='{station}'"

	logging.info(f"db query sql={sql}")
	try:
		mycursor = mydb.cursor()
		mycursor.execute(sql)
		rec = mycursor.fetchone()
		if rec is not None:
			logging.info(f"Caching lastSeen station ={station} timestamp={rec[0]}")
			lastSeen[station]=rec[0] # cache it
			return rec[0]
		else:
			logging.info(f"lastSeen for station {station} is None, check station name.")
			return None
	except Exception as e:
		logging.exception(F"Error trying to get last_seen for {station} error={e}")

################################################################################

mqtt_connected=False

def on_connect(mqttc, obj, flags, rc):
	# callback
	global mqtt_connected
	if rc == 0:
		logging.info("on_connect(): mqtt callback ok")
		mqtt_connected = True
	else:
		logging.info(f"on_connect(): callback error rc={rc}")

def connectToMqttBroker():
	global mqttc,mqtt_connected

	func = "connectToMqttBroker():"	# to reduce typing
	connected = False

	# connect to the client
	mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
	mqttc.on_connect = on_connect

	logging.info(f"{func} Trying to connect to mqtt broker")

	try:
		mqttc.connect(mqttBroker)
		mqttc.loop_start()
		# wait long enough for a connection callback
		logging.info(f"{func} waiting for on_connect callback")
		start=time.time()
		while not mqtt_connected:
			if time.time()-start>20:
				logging.info(f"{func} connect timed out (20s).")
				sys.exit(f"{func} No on_connect callback from MQTT broker in 20s")
			time.sleep(1)

		logging.info(f"{func} MQTT on_connect callback took %s s.",time.time()-start)

	except Exception as e:
		logging.exception(f"{func}Problem connecting to broker %s", str(e))
		sys.exit(f"{func} Unable to connect to MQTT broker") # wait for next cron


def formatted_timenow():
	# 2021-02-05T14:09:28
	return datetime.now().replace(microsecond=0).isoformat()

def iso_formatted_time(timestamp):
	return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()

def iso_formatted_dt(dt):
	return dt.replace(microsecond=0).isoformat()

def nested_dict():
	# define what a nested dictionary is - used to collect the sensor data
	return collections.defaultdict(nested_dict)

deviceData=nested_dict()    # data collected this time round

def collect_data_out(devName,data, sensor_type):
	global deviceData
	for entry in data["values"]:
		if int(entry["value"])>=0:
			timeStamp=entry["timestamp"]
			deviceData[devName][timeStamp][sensor_type] = entry["value"]
			deviceData[devName][timeStamp]["timestamp"] = iso_formatted_time(timeStamp / 1000)
			deviceData[devName][timeStamp]["dev"] = devName

connectToMqttBroker() # does sys.exit() on timeout/Exception

# the main loop
print("collecting data")

for station in stations.keys():
	msg=f"Processing station {station} data={stations[station]}"
	logging.info(msg)

	sensors=stations[station]["sensors"]	# a list [[id,reading_value_type],..]
	for sensor_id,sensor_type in sensors:

		last_seen=getLastSeen(station) # datetime object YYYY-mm-dd hh:mm:ss
		formatStr = "%Y-%m-%dT%H:%M:%S"

		if last_seen is not None:
			startDate = datetime.strftime(last_seen, formatStr)
		else:
			# not seen before
			startDate = datetime.now() - timedelta(days=never_seen)  # Typically 14 days ago
			startDate = datetime.strftime(startDate, formatStr)

		data_url = f"{main_url}{sensor_id}{append_url}{startDate}/{formatted_timenow()}"
		logging.info(f"data_url={data_url}")
		get_data = requests.get(data_url).json()

		if get_data.get("values") is not None: # any(get_data.get("values")) is True:
			collect_data_out(station,get_data, sensor_type)
		else:
			logging.info(f"No data for dev {station} sensor {sensor_id} type {sensor_type}")

logging.info("Sending data to MQTT broker")
print("Sending data")

for dev in deviceData:
	# do this in increasing timestamp order
	for ts in sorted(deviceData[dev]):
		value=json.dumps(deviceData[dev][ts])
		logging.info(f"json: {value}")
		if not debug:
			mqttc.publish(mqttTopic,value)
		else:
			logging.info(f"Would send json: {value}")

logging.info("Finished normally")
print("Finished")