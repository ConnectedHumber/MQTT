
"""
defraBridge V2.01.py

Downloads DEFRA sensor data and sends it to the MQTT broker for adding to the
sensor database.

This code is a modification of example code written by Ben Simmons

Data from all listed sensors is collected into a nested dict before being sorted and sent to the MQTT broker.
This allows all readings produced at the same time to be grouped as one message. The messages are sent
to the MQTT broker in ascending timestamp order so that the database devices.last_seen column always reflects the
latest readings.

Runs as a cron job, usually 15 minutes past the hour. DEFRA sites update on an hourly basis
but the data may not be available at the top of the hour. At times the data isn't available till
some considerable time later - notably at weekends. Missing data usually have a sensor value of -99.
This code ignores those readings.

install as defraBridge.py


Defra device settings are in DefraSettings.py. Note that if the device does not exist
in the database mqtt messages will be ignored. Also, if the message contains a sensor type which is not
listed in the database, e.g. NOX, it will be ignored.

Author: Brian N Norman
Date: 26/3/2021
Version: 2.01

"""
import requests
from datetime import datetime, timezone, timedelta
import collections
from DefraSettings import * #device_id,stations,location,main_url,append_url,never_seen
from settings import *
import logging
import mysql.connector
import paho.mqtt.client as paho
import sys
import time
import json
import os

# create PID file for monitoring
pid_file = open("/run/defraBridge/lastrun.pid", "w")
pid_file.write(str(os.getpid()))
pid_file.close()

logFile="/var/log/defraBridge/defraBridge.log"

# logging
logging.basicConfig(filename=logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)
logging.info(" ############################### ")
logging.info("Starting DEFRA sensor data collector")


mqttc = paho.Client()
lastSeen={} # updated from the aq_db database devices table

try:
        mydb= mysql.connector.connect(
                                host=dbHost,
                                user=dbUser,
                                passwd=dbPassword,
                                database=dbName
                        )
        logging.info("Database connection ok")

except Exception as e:
        logging.error("Database connection failed error=%s",e)
        sys.exit("Database connection failed to dbHost:"+str(dbHost))

########################################################################

def getLastSeen():
        """
        Populate lastSeen dict with values from the database
        lastSeen values are converted to datetime objects
        :return:
        """
        global lastSeen,mydb,device_id,logging
        baseSql = "select last_seen from devices where device_name='"
        logging.info("getLastSeen(): begins")
        lastSeen={}
        mycursor = mydb.cursor()

        for dev in device_id.keys():
                devName=device_id[dev]
                sql = baseSql+devName+"'"
                mycursor.execute(sql)
                rec = mycursor.fetchone()
                if rec is None:
                        lastSeen[devName]=None  # to ensure we try to include it later
                        logging.error(f"getLastSeen(): device_name '{devName}' not found in devices table.")
                else:
                        logging.info(f"getLastSeen(): Found device {devName} lastSeen {rec[0]}")
                        lastSeen[devName] = rec[0]


################################################################################

mqtt_connected=False

def on_connect(mqttc, obj, flags, rc):
        # callback
        global mqtt_connected
        print("on_connect rc=",rc)
        if rc == 0:
                logging.info("on_connect(): mqtt callback ok")
                mqtt_connected = True
        else:
                logging.info(f"on_connect(): callback error rc={rc}")

def connectToMqttBroker():
        global mqttc,mqtt_connected

        func = "connectToMqttBroker():" # to reduce typing
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

getLastSeen()   # populates lastSeen dict

for sensor_location, sensor_info in stations.items():
        logging.info(f"\nChecking DEFRA station {sensor_location}:")

        for sensor_id in sensor_info:
                # print(f"\nSensor at {sensor_id} has type {sensor_info[sensor_id]}")
                last_seen=lastSeen[device_id[sensor_location]] # datetime object YYYY-mm-dd hh:mm:ss
                formatStr = "%Y-%m-%dT%H:%M:%S"

                if last_seen is not None:
                        startDate = datetime.strftime(last_seen, formatStr)
                else:
                        # not seen before
                        startDate = datetime.now() - timedelta(days=never_seen)  # Typically 14 days ago
                        startDate = datetime.strftime(startDate, formatStr)

                data_url = f"{main_url}{sensor_id}{append_url}{startDate}/{formatted_timenow()}"
                #print("data_url=",data_url)
                get_data = requests.get(data_url).json()

                if get_data.get("values") is not None: # any(get_data.get("values")) is True:
                        collect_data_out(device_id[sensor_location],get_data, sensor_info[sensor_id])
                else:
                        logging.info(f"No data for dev {device_id[sensor_location]} sensor {sensor_id} type {sensor_info[sensor_id]}")

# repalce with publish commands
logging.info("Sending data to MQTT broker")

for dev in deviceData:
        for ts in sorted(deviceData[dev]):
                value=json.dumps(deviceData[dev][ts])
                #print(type(value),value) # replace with
                logging.info("publishing device data")
                mqttc.publish("airquality/data",value)

logging.info("Finished normally")
