#!/usr/bin/env python3
"""
ttnBridge.py

version: 1.1
author(s): Brian Norman/Robin Harris
date: 28/8/2019

purpose: to receive MQTT messages from TTN and repackage the payload for sending to the Connected Humber broker.

The program uses python queue to add jobs (callback) to be processed and deals with them
in the main loop.




"""

VERSION="1.0"   # for the log file

# note: do not import ttn before logging!! it kills the logger
import time
import json
import paho.mqtt.client as paho
import sys

if int(sys.version[0])>=3:
    import queue
else:
    import Queue as queue

# these will be put into a config file later
logFile="/var/log/ttnHccBridge.log"
app_id = 'hccsensortest'
access_key = '<ASK>'
MAX_JOBS=256    # arbitrary number
chClientUser="connectedhumber"
chClientPassword="<password here>"
chBroker="mqtt.connectedhumber.org"
chKeepAlive=60
chConnectTimeout=40
chClient=None   # Connected Humber MQTT client
chTopic="airquality/data"

try:
    import logging
    logging.basicConfig(filename=logFile,format='%(asctime)s %(message)s', level=logging.DEBUG)
    logging.info("\n###############################\n")
    logging.info("ttnBridge vsn%s starting"%VERSION)
    import ttn
except Exception as e:
    print("Logging failed",e)
    exit()




# circular buffer (FIFO) for TTN message callbacks to be processed
job_queue=queue.Queue(MAX_JOBS)

#####################################
#
# ttn_callback()
#
# device messages from TTN are queued for handling
#
def ttn_callback(msg, client):
    global job_queue

    thisPayload = {}
    thisPayload["dev"] = msg.dev_id
    thisPayload["temp"] = msg.payload_fields.celcius
    thisPayload["humidity"] = msg.payload_fields.humidity
    thisPayload["pressure"] = msg.payload_fields.mbar
    thisPayload["PM10"] = msg.payload_fields.pm_10
    thisPayload["PM25"] = msg.payload_fields.pm_25
    thisPayload["RSSI"] = msg.metadata.gateways[0].rssi
    thisPayload["gtw_id"] = msg.metadata.gateways[0].gtw_id
    thisPayload["timestamp"] = msg.metadata.time

    jsonPayload = json.dumps(thisPayload)
    job_queue.put(jsonPayload)

#####################################
#
# process_job()
#
# creates a CH friendly JSON string and publishes it
# to the CH broker. It is a blocking function
# using wait_for_publish() to ensure the CH broker
# got the message
#
def process_job(jsonPayload):
    global chClient

    logging.info("Sending payload %s",jsonPayload)
    print("Sending payload :",jsonPayload)
    (rc,mid)=chClient.publish(chTopic,jsonPayload)
    logging.info("process_job(): publish msg rc=%s mid=%s"%(str(rc),str(mid)))

###################################
#
# on_publish() callback
#
def on_publish(client,userdata,rc):
    logging.info("on_publish(): received callback %s"%str(rc))

###########################################################
#
# connectToCH()
#
# establishes a connection to the CH MQTT broker
# returns True on success otherwise False

def connectToCH():
    global chClient

    try:
        chClient = paho.Client()  # uses a random client id

        chClient.on_publish=on_publish

        # use authentication?
        if chClientUser is not None:
            logging.info("connectToCH(): using MQTT authentication")
            chClient.username_pw_set(username=chClientUser, password=chClientPassword)
        else:
            logging.info("connectToCH(): not using MQTT autentication")

        # terminate if the connection takes too long
        # on_connect sets a global flag chClient_connected

        chClient.loop_start()	# runs in the background, reconnects if needed
        chClient.connect(chBroker, keepalive=chKeepAlive)

    except Exception as e:
        logging.info("Unable to connect to mqtt broker %s", sys.exc_info()[0])
        return False

    else:
        print("connected to broker ok")
        logging.info("Connected to mqtt broker")
        return True

########################################################
#
# connectToTTN()
#
# create a client and connect it to the broker
# blocks till the first message is received
# which causes ttnClient_connected to be set True
def connectToTTN():
    logging.info("Connecting to TTN broker")
    handler = ttn.HandlerClient(app_id, access_key)
    ttnClient = handler.data()
    ttnClient.set_uplink_callback(ttn_callback)
    ttnClient.connect()
    logging.info("Connected to TTN broker")

########################################################
# main loop which retrieves jobs from the job_queue
# and passes them to process_job()
########################################################

# connect to the clients
# no point trying TTN if unable to connect to CH broker

if connectToCH():
    connectToTTN()

    while True:
        # anything to do?
        if not job_queue.empty():
            jsonPayload = job_queue.get()  # retrieve the next job
            process_job(jsonPayload)
        else:
            # wait nicely
            # allow system processes to run
            time.sleep(0.1)

chClient.disconnect()
logging.info("ttnBridge terminated.")


