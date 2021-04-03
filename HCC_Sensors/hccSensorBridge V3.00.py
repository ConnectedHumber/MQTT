#!/usr/bin/env python3
"""
hccSensorBridge V3.00.py (formerly hccTtnBridge)

version: 3.0
author(s): Brian Norman
date: 13/3/2021

purpose: to receive MQTT messages from TTN and repackage the payload for sending to the Connected Humber broker.

The program uses python queue to add jobs (callbacks) to be processed and deals with them
in the main loop.

"""


# note: do not import ttn before logging!! it appears to kill the logger
import time
import json
import paho.mqtt.client as paho
import sys
import os
import logging
import toml
import ttn
import queue


VERSION="3.0"   # for the log file
print("running on python ",sys.version[0])

# get config values and check they exist

sharedFile = "Shared.toml"
configFile = "hccSensorBridge.toml"

mqttClient=None

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
    logging.info(f"Starting HCC-TTN sensor data collector Vsn: {VERSION}")

    logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

    # mqtt - from Shared.toml
    mqttTopic = shared["mqtt"]["topic"]
    mqttClientUser = shared["mqtt"]["user"]
    mqttClientPassword = shared["mqtt"]["passwd"]
    mqttBroker = shared["mqtt"]["host"]
    mqttKeepAlive = shared["mqtt"]["keepAlive"]

    app_id = config["settings"]["app_id"]
    access_key = config["settings"]["access_key"]
    MAX_JOBS = config["settings"]["MAX_JOBS"]

except KeyError as e:
    errMsg = f"Config file entry missing: {e}"

    if logFile is not None:
        logging.exception(errMsg)
    sys.exit(errMsg)

except Exception as e:
    errMsg = (f"Unable to load settings from config file. Error was {e}")
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
    global mqttClient

    logging.info(f"Sending payload {jsonPayload}")
    if not debug:
        (rc,mid)=mqttClient.publish(mqttTopic,jsonPayload)
        logging.info(f"publish msg rc={rc} mid={mid}")
    else:
        logging.info(f"debug: would send to topic {mqttTopic} payload {jsonPayload}")
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
    global mqttClient

    try:
        mqttClient = paho.Client()  # uses a random client id

        mqttClient.on_publish=on_publish

        # use authentication?
        if mqttClientUser is not None:
            logging.info("using MQTT authentication")
            mqttClient.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
        else:
            logging.info("not using MQTT autentication")

        # terminate if the connection takes too long
        # on_connect sets a global flag mqttClient_connected

        mqttClient.loop_start()	# runs in the background, reconnects if needed
        mqttClient.connect(mqttBroker, keepalive=mqttKeepAlive)

    except Exception as e:
        logging.info("Unable to connect to mqtt broker %s", sys.exc_info()[0])
        return False

    else:
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

    logging.info("Waiting for ttn callbacks")

    while True:
        # anything to do?
        if not job_queue.empty():
            jsonPayload = job_queue.get()  # retrieve the next job
            process_job(jsonPayload)
        else:
            # wait nicely
            # allow system processes to run
            time.sleep(0.1)

mqttClient.disconnect()
logging.info("ttnBridge terminated.")


