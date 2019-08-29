#!/bin/env python3
#
# defraBridge.py
#
# version 1.10
#
# broker changed for new server
#
import requests
import json
from datetime import datetime, timedelta
import csv
import paho.mqtt.client as paho
import time
import logging

VERSION="1.10"	# used for logging

lastTimeStampFile="/home/CHAdmin/defraTimestamp.txt"

# log settings

logFile = '/var/log/defraBridge.log'
logging.basicConfig(filename=logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)

logging.info("###############################")
logging.info("Starting DEFRA sensor data collector")

# MQTT settings
mqttBroker = "51.140.15.143"						#'mqtt.connectedhumber.org'
mqttClientUser = "connectedhumber"
mqttClientPassword = "<ask>"
mqttTopic = "airquality/data"


def saveLastTimestamp(timestamp):
    fp=open(lastTimeStampFile,"w+")    # create if missing, overwrite otherwise
    fp.write(str(timestamp))
    fp.close()

def getLastTimestamp():
    try:
        fp = open(lastTimeStampFile, "r")
        ts=fp.readline()
        fp.close()
        logging.info("Last timestamp was %s",ts)
        return float(ts)
    except Exception as e:
        return None

def on_connect(mqttc, obj, flags, rc):
    if rc==0:
        logging.info("Connected to broker rc: %s", rc)
        mqttc.subscribe(mqttTopic)
    else:
        logging.info("Failed to connect to broker rc: %s", rc)

def on_message(mqttc, obj, msg):
    logging.info("got a message %s", str(msg.content))

def on_subscribe(mqttc,obj,mid,granted_qos):
    logging.info("Subscribed: " + str(mid))

mqttc = paho.Client()  # uses a random client id
mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_message = on_message
# connect to broker
logging.info("trying to connect to mqtt broker")
mqttc.loop_start()

try:
    mqttc.connect(mqttBroker)
    # wait for a connection
    time.sleep(3)
except Exception as e:
    logging.exception("Problem connecting to broker %s", str(e))

# get the current datetime as an object and add one day (so API gets data up to current)
dateTimeObject = datetime.now() + timedelta(days=1)
# create a string in the required format for get request
dateT = dateTimeObject.strftime('%Y-%m-%d')
# url has the current date added.  This requests the hourly data for 1 day previous to today.
urlTotal = 'https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/266/getData?timespan=P1D/' + dateT
req = requests.get(urlTotal)
logging.info("Status code from request: %s,", req.status_code)
json_response = json.loads(req.content.decode("utf-8"))
# the last reading in the list is the most recent hour data

# fake a negative
json_response['values'][-1]['value']=-66.66
#print(json_response)
lastValidEntry=-1
latestHour = json_response['values'][lastValidEntry]
while latestHour['value']<0:
    lastValidEntry=lastValidEntry-1
    latestHour = json_response['values'][lastValidEntry]

# get the timestamp from the latest entry in the response
latestTimestamp=latestHour['timestamp']/1000
lastTimestamp=getLastTimestamp()

logging.info("last recorded timestamp=%s, latest timestamp=%s",str(lastTimestamp),str(latestTimestamp))
if lastTimestamp is None or (latestTimestamp>lastTimestamp):
    logging.info("Using latest timestamp")
    saveLastTimestamp(latestTimestamp)

    t = datetime.fromtimestamp(latestTimestamp)
    # convert timestamp to the required mqtt format
    ts = t.strftime('"%a %b %d %Y %H:%M:%S %Z%zGMT+0000"')
    PM25 = latestHour['value']
    logging.info("Latest reading time: %s Value: %s", ts, PM25)


    # get the timestamp from the latest entry in the response
    t = datetime.fromtimestamp(latestTimestamp)
    # convert timestamp to the required mqtt format
    ts = t.strftime('"%a %b %d %Y %H:%M:%S %Z%zGMT+0000"')
    PM25 = latestHour['value']
    logging.info("Latest reading time: %s Value: %s", ts, PM25)
    # build a JSON string to send
    sendBuffer =  "{{\"dev\": \"UKA00450\", \"PM25\": {}, \"timestamp\": {}}}".format(PM25, ts)
    logging.info("sendBuffer: %s", sendBuffer)
    mqttc.publish(mqttTopic, sendBuffer)
    mqttc.loop_stop()

else:
    logging.info("lastTimeStamp stands")
