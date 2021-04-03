#!/usr/bin/python3
"""
connexinBridge V3.00.py (was clarityBridge.py)

Authors: Brian Norman
Date: 28/3/2021
Version: 3.0
Python Version: 3


Clarity device API interface

Collects data from connexins' clarity devices and passes data to ConnectedHumber MQTT broker

Note clarity data is hourly, there are no callbacks so this must run as a periodic systemd script once per hour

clarity API ref:
 https://clarity.io/documents/Clarity%20Air%20Monitoring%20Network%20REST%20API%20Documentation.html

V3.0 re-write of clarityBridge using TOML config files and some tidy up

"""
import requests
import json
from datetime import datetime, timedelta,tzinfo
from dateutil.parser import *
import paho.mqtt.client as paho
import time
import sys
import logging
import os
import toml

VERSION="3.0"   # used for logging
print("running on python ",sys.version[0])

# get config values and check they exist
configFile = "ConnexinBridge.toml"
sharedFile = "Shared.toml"

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

    # logging
    logging.basicConfig(filename=logFile, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logging.DEBUG)
    logging.info("############################### ")
    logging.info(f"Starting connexin clarity sensor data collector Vsn: {VERSION}")

    logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

    # mqtt
    mqttTopic = shared["mqtt"]["topic"]
    mqttClientUser = shared["mqtt"]["user"]
    mqttClientPassword = shared["mqtt"]["passwd"]
    mqttBroker = shared["mqtt"]["host"]
    mqttConnectTimeout= shared["mqtt"]["connectTimeout"]


    # program
    lastTimestampFile=config["settings"]["lastTimestampFile"]
    base_url=config["settings"]["base_url"]
    api_key =config["settings"]["api_key"]

    DEVPREFIX = config["settings"]["DEVPREFIX"]
    LOCATION =config["settings"] ["LOCATION"]
    COORDS = config["settings"]["COORDS"]
    MEASURES = config["settings"]["MEASURES"]
    VALUE = config["settings"]["VALUE"]
    ID = config["settings"]["ID"]
    DEVCODE = config["settings"]["DEVCODE"]
    TIME = config["settings"]["TIME"]
    LONGITUDE = config["settings"]["LONGITUDE"]
    LATITUDE = config["settings"]["LATITUDE"]
    TIMESTAMP = config["settings"]["TIMESTAMP"]

    aliases=config["aliases"]

except KeyError as e:
    errMsg = f"Config file entry missing: {e}"
    if logFile is not None:
        logging.exception(errMsg)
    sys.exit(errMsg)

except Exception as e:
    errMsg = (f"Unable to load settings from config file. Error was {e}")
    if logFile:
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
    logging.error(f"Non-fatal error writing to {pidFile} error {e}")


# dictionary used to collect sensor readings to be sent to connected humber
ch_data = {}

# mqtt client status
mqttc = paho.Client()   # uses a random client id
dataPublished=False     # flag to wait for publish to complete
brokerConnected=False   # flag to show the connection succeeded

# for checking that the data is new
lastTimestamp=None # set by getLastTimestamp()

#############################
#
# timestamps
#
# the api returns a timestamp. If you set the info window to wider than 1 hour
# you get multiple readings for one device but they all have the same
# timestamp so we store the last timestamp
# and ignore readings with the same timestamp
#
def saveLastTimestamp(timestamp):   # string '2019-08-16T12:00:00.000Z'
    logging.info("Saving last timestamp %s",timestamp)
    fp=open(lastTimestampFile,"w+")    # create if missing, overwrite otherwise
    fp.write(str(timestamp))
    fp.close()

def getLastTimestamp():
    try:
        fp = open(lastTimestampFile, "r")
        ts=fp.readline()
        fp.close()
        logging.info("Last timestamp was %s",ts)
        if ts=="None" or ts=="" or ts is None:
            ts="2018-08-01T00:00:00.000Z"
        return parse(ts)
    except FileNotFoundError:
        return parse("2018-08-01T00:00:00.000Z")


#############################
#
# getDevices()
#
# get device returns a list of device short codes for those flagged as working
# we use the shortcode as a Connected Humber device id
#
def getDevices():
    url = base_url+"/devices"
    logging.info("Querying url: %s", url)

    response = requests.get(url, headers={"x-api-key": api_key})
    if response.status_code!=200:
        logging.info("Got return code: %d",response.status_code)
        return None

    logging.info("Url request response was OK")

    dev_info=response.json()# returns a list encapsulating JSON
    working_list=[]
    for k in range(0,len(dev_info)):
        if dev_info[k]["lifeStage"]=="working":
            working_list.append(dev_info[k]["code"])
            logging.info("found device with code=%s",dev_info[k]["code"])
    if len(working_list)==0:
        logging.info("No devices found")
    return working_list

#############################
#
# getDeviceInfo(devices,startTime,endTime,average='hour')
#
# devices is a simple list of device codes
# startTime and endTime are python datetimes or None
# average is a string "hour" or "day" and defaults to 'hour'
#
# get the info for the chosen device(s) into a JSON object
#
def getDeviceInfo(devices,startTime=None,endTime=None,average="hour"):
    if devices is None:
        logging.error("List of devices required.")
        return None
    if len(devices)==0:
        logging.error("Device list is empty.")
        return None

    # build a URL for every occasion
    code=",".join(devices)

    url=""  # keep 'referenced before assignment' alert at bay
    if startTime is not None and endTime is not None:
        url = base_url+"/measurements?code={}&startTime={}&endTime={}&average={}"
        url = url.format(code,startTime.isoformat()+"Z",endTime.isoformat()+"Z",average)
    elif startTime is None and endTime is None:
        url = base_url + "/measurements?code={}&average={}"
        url = url.format(code, startTime.isoformat() + "Z", endTime.isoformat() + "Z", average)
    elif startTime is None and endTime is not None:
        url = base_url+'/measurements?code={}&endTime={},&average={}'
        url = url.format(code, endTime.isoformat() + "Z", average)
    elif endTime is None and startTime is not None:
        url = base_url + '/measurements?code={}&startTime={},&average={}'
        url = url.format(code, startTime.isoformat() + "Z", average)

    logging.info(f"url={url}")
    logging.info(f"api_key={api_key}")

    response = requests.get(url, headers={"x-api-key": api_key})

    if response.status_code!=200:
        logging.error(f"Got return code:{response.status_code}")
        return None

    return response.json()


################
# addKeyValue(key,value)
#
# if key is in the alias list we add to the
# ch_data dictionary, otherwise we ignore it

def addKeyValue(key, value):
    # ignore keys not in our alias list
    if not key in aliases:
        return

    # most decimal numbers e.g. temp, humidity
    # only require 2 digit precision
    # lat and lon are different
    if type(value) is float:
        if key != LATITUDE and key != LONGITUDE:
            value = round(value, 2)

    # get clarity key,
    ch_key = aliases[key]
    if ch_key is not None:  # belt and braces
        ch_data[ch_key] = value

###############################################################
#
# MQTT broker
#
# we only connect once then publish our findings

def on_publish(client, obj, flags, rc):
    global dataPublished

    dataPublished=True

def on_connect(client, obj, flags, rc):

    global ch_data,brokerConnected,dataPublished

    brokerConnected=False

    if rc==0:
        brokerConnected=True
        logging.info("Connected to broker ok")
    else:
        logging.info("Failed to connect to broker rc: %s", rc)

def connectToBroker():

    global mqttc

    mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
    mqttc.on_connect = on_connect  # callback received when connected
    mqttc.on_publish = on_publish  # callback received when the message has published

    mqttc.loop_start()

    try:
        mqttc.connect(mqttBroker)

        # wait for a connection callback
        # the callback publishes the ch_data
        start = time.time()
        while not brokerConnected:
            if (time.time() - start) > mqttConnectTimeout:
                logging.error(f"Unable to connect to broker in {mqttConnectTimeout} s")
                return False
        logging.info("Connected to broker ok")
        return True

    except Exception as e:
        logging.exception(f"Problem connecting to broker. Error = {e}")
        return False

def sendToBroker():
    global ch_data,dataPublished

    dataPublished = False
    logging.info("Sending to broker.")
    jsonPayload = json.dumps(ch_data)

    # debugging
    if not debug:
        logging.info("Publishing payload={jsonPayload}")
        mqttc.publish(mqttTopic, jsonPayload)
    else:
        logging.info("debug : would publish payload={jsonPayload}")

#############################################################
#
# main
#
#############################################################

# establish an MQTT connection
if not connectToBroker():
    # no point continuing
    exit()

# this returns a timestamp or parsed "2018-08-01T00:00:00.000Z"
lastTimestamp=getLastTimestamp()

# get a list of working devices
device_list=getDevices()
if device_list is None:
    logging.info("No devices to process")
    exit()

# get a dictionary of device information use default for average
# time window is 1 hour from 2 hours ago
# note that 1 hour back from now() returns nothing

startTime=datetime.now()-timedelta(hours=2)
endTime=datetime.now()-timedelta(hours=1)
logging.info("startTime=%s, endTime=%s",startTime,endTime)
# get the device info list
device_info=getDeviceInfo(device_list,startTime,endTime)

if device_info is None:
    logging.info("No device info returned.")
    exit()

logging.info("device_info %s",device_info)
###############################################
#
# process the devices
# put the data into a dictionary for sending to
# connected humber
#
###############################################

thisTimestamp=None  # all readings in a 1 hour window have the same timestamp

logging.info("processing all device info")

for dev in range(0,len(device_info)):

    ch_data={}  # new device

    this_dev=device_info[dev]

    logging.info("this dev_info %s", this_dev)

    for k in this_dev.keys():
        logging.info("this dev_info", this_dev)
        if k==LOCATION:
            #split lat/lon into sep values
            # lat/lon will not change as the devices are static
            lon,lat=this_dev[k][COORDS]
            addKeyValue(LONGITUDE,lon)
            addKeyValue(LATITUDE,lat)
        elif k==DEVCODE:
            # connected humber dev format "CL-"+Clarity deviceCode
            addKeyValue(DEVCODE,DEVPREFIX+this_dev[DEVCODE])
        elif k=='time':
            addKeyValue(TIMESTAMP,this_dev[k])
            thisTimestamp=parse(this_dev[k])
        elif k==MEASURES:
            # measurements
            measures=this_dev[k]
            for m in measures.keys():
                addKeyValue(m,measures[m][VALUE])
        else:
            addKeyValue(k,this_dev[k])


    #print("lastTimestamp=",lastTimestamp)
    #print("thisTimestamp=",thisTimestamp)

    logging.info("Preparing to send to broker")
    # send ch_data for this device to the broker
    if thisTimestamp is not None:
        if thisTimestamp>lastTimestamp:
            if sendToBroker():
                logging.info("main(): data was sent to broker ok")
                #print("Would send...",ch_data)
            else:
                logging.warning("main(): sendToBroker Failed.")

        else:
            logging.info("main(): Reading timestamp (%s) already seen - data not sent.",this_dev[TIMESTAMP])
    else:
        logging.error("main(): this dev_info timestamp was None")

# all done ... record the timestamp
if thisTimestamp is not None:
    saveLastTimestamp(thisTimestamp)
mqttc.loop_stop()

logging.info("Finished normally")