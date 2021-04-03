
#----------------------------------------------------------------------------------------------------------
#
# clarityBridge.py
#
# --- Authors: Brian Norman
# --- Date: 26th March 2021
# --- Version: 1.0
# --- Python Version: 3
#
#
# Clarity API interface
#
# Collects data from clarity devices and passes to ConnectedHumber MQTT broker
#
# Note clarity data is hourly, there are no callbacks so this must run
# as a periodic cron script or systemd timer once per hour
#
# clarity API ref:
# https://clarity.io/documents/Clarity%20Air%20Monitoring%20Network%20REST%20API%20Documentation.html
#
#
#---------------------------------------------------------------------------------------------------------
VERSION="1.0"   # used for logging

import sys,logging,os
print("running on python ",sys.version[0])

from ClaritySettings import *   # ClaritySettings.py in this folder

import requests
import json
from datetime import datetime, timedelta,tzinfo
from dateutil.parser import *
import paho.mqtt.client as paho
import time
import os


# create PID file for monitoring
pid_file = open("/run/clarityBridge/lastrun.pid", "w")
pid_file.write(str(os.getpid()))
pid_file.close()

# log settings and log file header
logging.basicConfig(filename=logFile,format='%(asctime)s %(message)s', level=logging.DEBUG)

thisScript=os.path.basename(__file__)
logging.info("#############################")	# make it easy to see the restart
logging.info("%s Version %s begins",thisScript,VERSION)

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
    fp=open(lastTimestampFile,"w+")    # create if missing, overwrite otherwise
    fp.write(str(timestamp))
    fp.close()

def getLastTimestamp():
    try:
        fp = open(lastTimestampFile, "r")
        ts=fp.readline()
        fp.close()
        logging.info("Last timestamp was %s",ts)
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

    dev_info=response.json()# returns a list encapsulating JSON
    working_list=[]
    for k in range(0,len(dev_info)):
        if dev_info[k]["lifeStage"]=="working":
            working_list.append(dev_info[k]["code"])
            logging.info("getDevices found device with code=%s",dev_info[k]["code"])

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
        logging.error("getDeviceInfo() requires a list of devices.")
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

    logging.info("getDeviceInfo() url=%s",url)
    logging.info("getDeviceInfo() api_key=%s", api_key)

    response = requests.get(url, headers={"x-api-key": api_key})

    if response.status_code!=200:
        logging.error("getDeviceInfo() Got return code:",response.status_code)
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
                logging.error("connectToBroker(): Unable to connect to broker in %ds", mqttConnectTimeout)
                return False
        logging.info("connectToBroker(): Connected to broker")
        return True

    except Exception as e:
        logging.exception("ConnectToBroker(): Problem connecting to broker %s", str(e))
        return False

def sendToBroker():
    global ch_data,dataPublished

    dataPublished = False
    logging.info("sendToBroker(): Sending to broker.")
    jsonPayload = json.dumps(ch_data)

    # debugging
    print("Publishing",jsonPayload)
    mqttc.publish(mqttTopic, jsonPayload)

    # wait for callback before sending next
    start = time.time()
    while not dataPublished:
        if (time.time() - start) > mqttPublishTimeout:
            logging.error("sendToBroker(): Publish timeout after %ds", mqttPublishTimeout)
            return False
    return True


#############################################################
#
# main
#
#############################################################

# establish an MQTT connection
if not connectToBroker():
    # no point continuing
    exit()

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

# get the device info list
device_info=getDeviceInfo(device_list,startTime,endTime)

if device_info is None:
    logging.info("No device info returned.")
    exit()

###############################################
#
# process the devices
# put the data into a dictionary for sending to
# connected humber
#
###############################################

thisTimestamp=None  # all readings in a 1 hour window have the same timestamp

for dev in range(0,len(device_info)):

    ch_data={}  # new device

    this_dev=device_info[dev]
    for k in this_dev.keys():

        if k==LOCATION:
            #split lat/lon into sep values
            # lat/lon will not change as the devices are static
            lon,lat=this_dev[k][COORDS]
            addKeyValue(LONGITUDE,lon)
            addKeyValue(LATITUDE,lat)
        elif k==DEVCODE:
            # connected humber dev format "CL-"+Clarity deviceCode
            addKeyValue(DEVCODE,DEVPREFIX+this_dev[DEVCODE])
        elif k==TIME:
            addKeyValue(TIME,this_dev[k])
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

    # send ch_data for this device to the broker
    if thisTimestamp is not None:
        if thisTimestamp>lastTimestamp:
            if sendToBroker():
                logging.info("main(): data was sent to broker ok")
                #print("Would send...",ch_data)
            else:
                logging.warning("main(): sendToBroker Failed.")

        else:
            logging.info("main(): Reading timestamp (%s) already seen - data not sent.",this_dev["TIME"])
    else:
        logging.error("main(): thisTimestamp")

# all done ... record the timestamp
saveLastTimestamp(thisTimestamp)
mqttc.loop_stop()
