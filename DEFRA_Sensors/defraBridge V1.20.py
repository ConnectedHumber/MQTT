#!/bin/env python3
#
# defraBridge V1.20.py
#
# called defraBridge.py when installed
#
# version 1.20
#
# 5/10/2019 changed logic to reduce chances of missing readings
# broker changed for new server
#
import requests
import json
from datetime import datetime, timedelta
import csv
import paho.mqtt.client as paho
import time
import logging

VERSION="1.20"	# used for logging
HISTORY="P3D"     # days of data to collect to ensure we don't miss any

lastTimeStampFile="/home/CHAdmin/defraTimestamp.txt"

# log settings

logFile = '/var/log/defraBridge.log'
logging.basicConfig(filename=logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)

logging.info(" ############################### ")
logging.info("Starting DEFRA sensor data collector")

# MQTT settings
mqttBroker = "broker"
mqttClientUser = "user"
mqttClientPassword = "password"
mqttTopic = "airquality/data"

# last timestamp recording and retrieving
def saveLastTimestamp(timestamp):
    fp=open(lastTimeStampFile,"w+")    # create if missing, overwrite otherwise
    fp.write(str(timestamp))
    fp.close()

def getLastTimestamp():
    try:
        fp = open(lastTimeStampFile, "r")
        ts=fp.readline()
        fp.close()
        if ts=="":
            logging.info("No stored timestamp")
            return None
        logging.info("Last timestamp was %s",ts)
        try:
            return float(ts)
        except:
            logging.info("Unable to convert %s to a float. returning None", ts)
            return None
    # if the file doesn't exist or the read fails
    except Exception as e:
        logging.info("Error getting last timestamp - assuming None")
        return None

# MQTT callbacks

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

# start the MQTT client

mqttc = paho.Client()  # uses a random client id
mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_message = on_message
# connect to broker
logging.info("Trying to connect to mqtt broker")
mqttc.loop_start()

try:
    mqttc.connect(mqttBroker)
    # wait for a connection callback
    time.sleep(3)
except Exception as e:
    logging.exception("Problem connecting to broker %s", str(e))
    exit()

#############################################################################################
# get the current datetime as an object and add one day (so API gets data up to current date)
dateTimeObject = datetime.now()+timedelta(days=1)   # end date for time series (tomorrow)
dateT = dateTimeObject.strftime('%Y-%m-%d') 		# create a string in the required format for get request
logging.info("Using timeseries end date: %s HISTORY=%s", dateT,HISTORY)

# return the data for the requested period
# The defra site does not update on the hour but provides hourly readings.
# This method tries to make sure we don't miss any of those readings
# dateT is now. History is typically "P3D" - period of 3 days
# so this URL returns the readings for 3 days leading up to now

urlTotal = 'https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/266/getData?timespan='+HISTORY+'/' + dateT
req = requests.get(urlTotal)
logging.info("Status code from request: %s,", req.status_code)
json_response = json.loads(req.content.decode("utf-8"))

# get timestamp of last reading
lastTimestamp=getLastTimestamp()
logging.info("Last timestamp= %s",str(lastTimestamp))

# scan for new timestamps
# we may have missed a reading (or two) when the previous cron job ran
# I have seen the weekend readings delayed
timestampList={}    # list[timestamp]=value
maxTimestamp=0;     # used to record latest timestamp value

# scan through returned values
for entry in json_response['values']:
    thisTimestamp=entry['timestamp']/1000.0
    maxTimestamp=max(maxTimestamp,thisTimestamp)

    # human readable
    t = datetime.fromtimestamp(thisTimestamp)
    ts = t.strftime('"%a %b %d %Y %H:%M:%S %Z%zGMT+0000"')

	# sometimes defra sends -99 which messes up the vertical axis of the charts
	if float(entry['value'])<0: entry['value']=-1.0
	
    # keep readings we haven't seen before
    if lastTimestamp is None or thisTimestamp>lastTimestamp:
        # new reading found
        logging.info("New timestamp= %s, value= %s",ts,str(entry['value']))
        timestampList[thisTimestamp]=entry['value']
    else:
        # reading is older but log it for a warm glow when debugging
        logging.info("Old timestamp= %s, value= %s IGNORED",ts,str(entry['value']))

# was there any new data?
if len(timestampList)==0:
    logging.info("No new data to add")
    mqttc.loop_stop()
    exit()

logging.info("Using max timestamp %s",str(maxTimestamp))

#print("Sorted timestampList=",sorted(timestampList.keys()))

# scan the list of readings in ascending order of timestamp
# and send them via MQTT
for TS in sorted(timestampList.keys()):
    #print("using TS=",TS)
    #human readable
    t = datetime.fromtimestamp(TS)
    ts = t.strftime('"%a %b %d %Y %H:%M:%S %Z%zGMT+0000"')
    PM25 = timestampList[TS]
    logging.info("Sending new reading via MQTT Timestamp: %s Value: %s", ts, PM25)

    # build a JSON string to send
    sendBuffer = "{{\"dev\": \"UKA00450\", \"PM25\": {}, \"timestamp\": {}}}".format(PM25, ts)
    logging.info("sendBuffer: %s", sendBuffer)
    mqttc.publish(mqttTopic, sendBuffer)

# tidy up and wait for next cron run
saveLastTimestamp(maxTimestamp)
mqttc.loop_stop()

