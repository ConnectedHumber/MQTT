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
import queue
from socket import error as SktErr



VERSION="3.0"   # for the log file
print("running on python ",sys.version[0])

# get config values and check they exist

sharedFile = "Shared.toml"
configFile = "hccSensorBridge.toml"
logFile=None
ttnClient= paho.Client()
chClient = paho.Client()
ttnConnected=False
chConnected=False

try:
    config = toml.load(configFile)
    shared = toml.load(sharedFile)

    debug = config["debug"]["settings"]["debug"]

    if debug:
        logFile = config["debug"]["settings"]["logFile"]
        pidFile = config["debug"]["settings"]["pidFile"]
    else:
        logFile = config["settings"]["logFile"]
        pidFile = config["settings"]["pidFile"]

    # logging
    logging.basicConfig(filename=logFile, format='%(asctime)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s', level=logging.DEBUG)
    logging.info("############################### ")
    logging.info("Starting hccSensorBridge data collector Vsn: %s",VERSION)

    logging.info(f"debug={debug}, logFile={logFile} , pidFile={pidFile}")

    mqttRc=shared["mqtt_rc"]

    # CH mqtt - from Shared.toml
    chTopic = shared["mqtt"]["topic"]
    chClientUser = shared["mqtt"]["user"]
    chClientPassword = shared["mqtt"]["passwd"]
    chBroker = shared["mqtt"]["host"]
    chKeepAlive = shared["mqtt"]["keepAlive"]

    app_id = config["settings"]["app_id"]
    access_key = config["settings"]["access_key"]
    ttnBroker=config["settings"]["ttnBroker"]
    ttnPort=config["settings"]["port"]
    ttnKeepAlive=config["settings"]["keepAlive"]
    MAX_JOBS = config["settings"]["MAX_JOBS"]
    max_not_seen = config["settings"]["max_not_seen"]
    max_not_seen_retries = config["settings"]["max_not_seen_retries"]

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
# process_job()
#
# creates a CH friendly JSON string and publishes it
# to the CH broker. It is a blocking function
# using wait_for_publish() to ensure the CH broker
# got the message
#
def process_job(jsonPayload):
    global chClient

    logging.info(f"Sending payload {jsonPayload}")
    if not debug:
        (rc,mid)=chClient.publish(chTopic,jsonPayload)
        logging.info(f"publish msg rc={rc} mid={mid}")
    else:
        logging.info(f"debug: would send to topic {chTopic} payload {jsonPayload}")

###################################
#
# ch_on_connect() callback
#
# callbacks from CH mqtt server
#
def ch_on_connect(client, userdata, flags,rc):
    global chConnected
    if rc==0:
        logging.info("connected to CH server ok")
        chConnected=True
    else:
        logging.info(f"ch_on_connect(): {mqttRc[rc]}")

###################################
#
# ch_on_publish() callback
#
# callbacks from CH mqtt server
#
def ch_on_publish(client,userdata,rc):
    logging.info(f"ch_on_publish(): received callback {rc}")

#####################################
#
# ttn_on_message()
#
# device messages from TTN are queued for handling
#
def ttn_on_message(client, obj,msg):
    global job_queue

    logging.info(f"recieved msg {msg.payload}")
    
    JSON=json.loads(msg.payload)

    logging.debug(f"parsedJSON={JSON}")
    
    chPayload = {}
    
    try:
        # TTN V3
        
        chPayload["dev"] = JSON["end_device_ids"]["device_id"]
        
        payload_fields=JSON['uplink_message']['decoded_payload']

        if payload_fields:
            chPayload["temp"] = payload_fields["celcius"]
            chPayload["humidity"] = payload_fields["humidity"]
            chPayload["pressure"] = payload_fields["mbar"]
            chPayload["PM10"] = payload_fields["pm_10"]
            chPayload["PM25"] = payload_fields["pm_25"]
        
        gw_metadata=JSON["uplink_message"]["rx_metadata"][0]
        
        chPayload["RSSI"] = gw_metadata["rssi"]
        chPayload["gtw_id"] = gw_metadata["gateway_ids"]["gateway_id"]
        chPayload["timestamp"] = JSON["uplink_message"]["received_at"]
        
        jsonPayload = json.dumps(chPayload)
        logging.info(f"on_message payload {chPayload}")
        job_queue.put(jsonPayload)
    
    except Exception as e:
        logging.exception(f"Exception decoding msg - {e}")
        return



    

###################################
#
# ttn_on_connect() callback
#
# callbacks from CH mqtt server
#
def ttn_on_connect(client,userdata,flags,rc):
    global ttnConnected,ttnClient
    if rc==0:
        logging.info("connected to TTN server ok")
        ttnClient.subscribe("#",0)
        ttnConnected=True
    else:
        logging.info(f"ttn_on_connect():  {mqttRc[rc]}")

###################################
#
# ttn_on_subscribe() callback
#
# callbacks from CH mqtt server
#
def ttn_on_subscribe(client,obj,mid,granted_qos):
    logging.info(f"subscribed to TTN server ok granted_qos={granted_qos}")
 

###########################################################
#
# connectToCH()
#
# establishes a connection to the CH MQTT broker
# returns True on success otherwise False

def connectToCH():
    global chClient

    try:

        # we are not expecting subscription messages
        chClient.on_publish = ch_on_publish
        chClient.on_connect = ch_on_connect
        # use authentication?
        if chClientUser is not None:
            logging.info("CH client using MQTT authentication")
            chClient.username_pw_set(username=chClientUser, password=chClientPassword)
        else:
            logging.info("CH client not using MQTT autentication")

        # terminate if the connection takes too long
        # on_connect sets a global flag mqttClient_connected

        chClient.loop_start()	# runs in the background, reconnects if needed
        chClient.connect(chBroker, keepalive=chKeepAlive)
        logging.info("waiting for CH on_connect callback")
        return True

    except Exception as e:
        logging.exception(f"Unable to connect to mqtt broker error: {e}")   #, sys.exc_info()[0])
        return False


########################################################
#
# connectToTTN()
#
# create a client and connect it to the broker
# blocks till the first message is received
# which causes ttnClient_connected to be set True


def connectToTTN():
    global ttnClient,app_id,access_key,ttnPort,ttnKeepAlive

    ttnClient.on_message = ttn_on_message
    ttnClient.on_connect = ttn_on_connect
    ttnClient.on_subscribe=ttn_on_subscribe

    ##logging.debug(f"Connecting to TTN with app_id {app_id} access_key {access_key} port {ttnPort} and keepAlives {ttnKeepAlive}")

    logging.info("Connecting to TTN")

    try:
        ttnClient.username_pw_set(app_id, access_key)
        ttnClient.tls_set()  # default certification authority of the system
        ttnClient.loop_start()
        ttnClient.connect(ttnBroker, ttnPort, ttnKeepAlive)

        logging.info("Waiting for TTN on_connect callback")
        return True

    except Exception as e:
        logging.exception(f"Exception connecting to TTN: {e}")
        return False
########################################################
# main loop which retrieves jobs from the job_queue
# and passes them to process_job()
########################################################

# connect to the clients
# no point trying TTN if unable to connect to CH broker

if connectToCH() and connectToTTN():

    if not ttnConnected or not chConnected:
        logging.info(f"Waiting for mqtt connect. ttn {ttnConnected} ch {chConnected}")

    start=time.time()
    while not ttnConnected or not chConnected:
        if (time.time()-start)>60:
            logging.error(f"on_connect failed after 60s ttnConnected:{ttnConnected} chConnected:{chConnected}")
            exit("connect failed")

    logging.info("Waiting for ttn message callbacks")

    while True:
        # anything to do?
        try:
            if not job_queue.empty():
                jsonPayload = job_queue.get()  # retrieve the next job
                process_job(jsonPayload)
        except SktErr as e:
            logging.error(f"Socket error {e}")
            chClient.disconnect()
            ttnClient.disconnect()
            exit("Socket error")

        # wait nicely
        # allow system processes to run
        time.sleep(0.1)




chClient.disconnect()
ttnClient.disconnect()
logging.info("hccSensorBridge terminated.")


