#!/bin/env python3
#
# defraBridge V1.30.py
#
# called defraBridge.py when installed
#
# version 1.30
#
# 2/11/2019 changed station id and url, remove csv import
# changed the url 'timespan' as the last one was broken (by DEFRA)
#
# 5/10/2019 changed logic to reduce chances of missing readings
# broker changed for new server
#
import requests
import json
from datetime import datetime, timedelta
import paho.mqtt.client as paho
import time
import logging

VERSION="1.20"	# used for logging
TIMESPAN=14     # days ago for first reading used if lastTimestamp is None
STATION_ID="2126"   # seems to hav changed - was 266
DEVICE_NAME="UKA00450-02"
baseUrl='https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/'+STATION_ID+'/getData?'

# log and timestamp file settings
DEBUG=False  # set to False for live system.
if DEBUG:
    logFile="defraBridge.log"
    lastTimeStampFile = "defraTimestamp.txt"
else:
    logFile = '/var/log/defraBridge.log'
    lastTimeStampFile = "/home/CHAdmin/defraTimestamp.txt"

logging.basicConfig(filename=logFile, format='%(asctime)s %(message)s', level=logging.DEBUG)

logging.info(" ############################### ")
logging.info("Starting DEFRA sensor data collector")

# MQTT settings
mqttBroker = 'mqtt.connectedhumber.org'
mqttClientUser = "ask"
mqttClientPassword = "ask"
mqttTopic = "airquality/data"

# last timestamp recording and retrieving
def saveLastTimestamp(timestamp):
    logging.info("Save last timestamp %s",timestamp)
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
# work out the interval to get data for
# note that there may be repeated values as days overlap
# but the code which adds the data will reject those seen before

# get timestamp of last reading
lastTimestamp=getLastTimestamp()
logging.info("Last timestamp= %s",str(lastTimestamp))

# start from last timestamp or TIMESPAN days ago
# this allows the code to catchup with readings missed in the last TIMESPAN days
# lastTimestamp is for the last valid reading processed

if lastTimestamp is not None:
    startDateTimeObject = datetime.fromtimestamp(lastTimestamp)     #
    startDateT = startDateTimeObject.strftime('%Y-%m-%d')         # required format for get request
else:
    # default to picking up from TIMESPAN days ago
    startDateTimeObject = datetime.now() - timedelta(days=TIMESPAN)  # TIMESPAN days ago
    startDateT = startDateTimeObject.strftime('%Y-%m-%d')            # required format for get request

# end of today
endDateTimeObject = datetime.now() + timedelta(days=1)
endDateT = endDateTimeObject.strftime('%Y-%m-%d')

logging.info("Using timeseries startDate : '%s' and end date: '%s'", startDateT,endDateT)

# return the data for the requested period
# The defra site does not update on the hour but provides hourly readings.
# This method tries to make sure we don't miss any of those readings
# dateT is now. History is typically "P3D" - period of 3 days
# so this URL returns the readings for 3 days leading up to now

defraUrl = baseUrl+'timespan='+startDateT+"/"+endDateT

req = requests.get(defraUrl)
logging.info("Status code from request: %s", req.status_code)
if req.status_code!=200:
    mqttc.loop_stop()
    exit()

json_response = json.loads(req.content.decode("utf-8"))



# scan for new timestamps
# we may have missed a reading (or two) when the previous cron job ran
# I have seen the weekend readings delayed
timestampList={}    # list[timestamp]=value
maxTimestamp=0;     # used to record latest timestamp value

# scan through returned values
for entry in json_response['values']:
    thisTimestamp=entry['timestamp']/1000.0
    maxTimestamp=max(maxTimestamp,thisTimestamp)

    # human readable for the log file
    t = datetime.fromtimestamp(thisTimestamp)
    ts = t.strftime('"%a %b %d %Y %H:%M:%S %Z%zGMT+0000"')

    # sometimes defra returns -99, bless! And that messes up the
    ## chart vertical axis
    if float(entry['value'])<0: entry['value']=-1.0;

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
    sendBuffer = "{{\"dev\": \"{}\", \"PM25\": {}, \"timestamp\": {}}}".format(DEVICE_NAME,PM25, ts)
    logging.info("sendBuffer: %s", sendBuffer)
    #mqttc.publish(mqttTopic, sendBuffer)

# tidy up and wait for next cron run
saveLastTimestamp(maxTimestamp)
mqttc.loop_stop()

