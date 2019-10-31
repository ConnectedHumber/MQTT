"""
devManager.py

runs on the database machine as a service using systemctl

Author:     Brian Norman
Date:       30/10/2019
Version:    1.0

subscribes to the broker for messages on topic devMgr

messages are passed to devProcessor.py and replies published
so that the originator can see the results.

The message and reply are json strings (See devProcessor.py


"""

import json
import paho.mqtt.client as paho
import mysql.connector
import time
import logging
import sys
import devProcessor

logFile="/var/log/devManager.log"

mqttBroker =        'broker' # PINAT test'51.140.15.143'    'mqtt.connectedhumber.org'
mqttClientUser =    "clientname"
mqttClientPassword = "password"
mqttListenTopic =   "/devMgr/install"
mqttReplyTopic=     "/devMgr/reply"

mqttConnectTimeout=20	# only checked on startup
mqttKeepAlive=60		# client pings server if no messages have been sent in this time period.
MAX_MESSAGE_NUMBER=9999
MAX_JOBS=100

dbHost="localhost"      # dbUser must have all privileges
dbUser="dbUser"
dbPassword="dbPassword"
dbName="aq_db"

msgHandler=None         # here to keep PyCharm happy
# initialise logging
logging.basicConfig(filename=logFile,format='%(asctime)s %(message)s', level=logging.DEBUG)

# initialise job queing
if int(sys.version[0])>=3:
    import queue
else:
    import Queue as queue

job_queue=queue.Queue(MAX_JOBS)


############################################################################
#
# processJob(jobNo,jsonString)
#
# jsonString is the payload from the received MQTT message
#
#
def processJob(jobNo,jsonString):
    global mqttc,mqttReplyTopic
    reply=msgHandler.decodeJSON(jobNo,jsonString)
    mqttc.publish(mqttReplyTopic,reply)

#####################################
#
# on_connect() callback from MQTT broker
#
def on_connect(mqttc, obj, flags, rc):
    global brokerConnected,mqttListenTopic,logging

    if rc==0:
        brokerConnected=True
        logging.info("on_connect(): callback ok, subscribing to Topic: %s",mqttListenTopic)
        mqttc.subscribe(mqttListenTopic, 0)
    else:
        brokerConnected=False
        logging.info("on_connect(): callback error rc=%s",str(rc))

################################
#
# on_message() MQTT broker callback
#
# UTF-8 decode the payload and add it to the job queue see main()
# jobs are processed in the order received
#
def on_message(mqttc, obj, msg):
    global job_queue,logging
    logging.info("on_message() received payload=%s",msg.payload)
    job_queue.put(msg.payload.decode("UTF-8"))

################################
#
# on_subscribe(0 MQTT Broker callback
#
# information only
#
def on_subscribe(mqttc,obj,mid,granted_qos):
    global logging
    logging.info("on_subscribe(): Subscribed with mid=%s",str(mid))


################################
#
# connectToBroker
#
# on_connect sets a global flag brokerConnected
def connectToBroker():
    global mqttc,brokerConnected,logging,mqttConnectTimeout

    brokerConnected=False

    logging.info("connectTobroker(): Trying to connect to the MQTT broker")

    mqttc = paho.Client()  # uses a random client id

    # NOTE: not listening for on_publish
    mqttc.on_connect = on_connect
    mqttc.on_subscribe = on_subscribe
    mqttc.on_message = on_message

    # use authentication?
    if mqttClientUser is not None:
        logging.info("connectToBroker(): using MQTT authentication")
        mqttc.username_pw_set(username=mqttClientUser, password=mqttClientPassword)
    else:
        logging.info("main(): not using MQTT autentication")

    # terminate if the connection takes too long
    # on_connect sets a global flag brokerConnected
    startConnect = time.time()
    mqttc.loop_start()	# runs in the background, reconnects if needed
    mqttc.connect(mqttBroker, keepalive=mqttKeepAlive)

    while not brokerConnected:
        if (time.time() - startConnect) > mqttConnectTimeout:
            logging.error("connectToBroker(): broker on_connect time out (%ss)", mqttConnectTimeout)
            print("connectToBroker: failed to connect to MQTT broker within timeout.")
            return False

    logging.info("connectToBroker(): Connected to MQTT broker after %s s", int(time.time() - startConnect))
    return True

###################################
#
# connectToDatabase()
#
# attempt to connect to the database
# return True on success else False
#
def connectToDatabase():
    global mydb,dbHost,dbUser,dbPassword,dbName,logging
    # open a database connection
    try:
        mydb = mysql.connector.connect(
            host=dbHost,
            user=dbUser,
            passwd=dbPassword,
            database=dbName
        )

        logging.info("connectToDatabase(): Opened a database connection ok.")
        return True

    except Exception as e:
        logging.exception("main(): Unable to connect to the database.")
        return False


#############################################################################
#
# main
#
#############################################################################


# try to connect to the database
if not connectToDatabase():
    mqttc.loop_stop()
    sys.exit()

# try to connect to the broker
if not connectToBroker():
    mqttc.loop_stop()
    sys.exit()


# create a device processor instance
msgHandler=devProcessor.msgHandler(mydb)

# main loop which retrieves jobs from the job_queue
# and passes them to process_job()

message_number=0    # initial value after restart
try:
    while True:
        # anything to do?
        if not job_queue.empty():
            # make sure the dabase is alive and well
            mydb.ping(reconnect=True, attempts=5, delay=1)
            # TODO add code to check if the connection is really up
            # retrieve the next job and process it
            processJob(message_number,job_queue.get())
            # bump the message number with wrap around
            message_number=(message_number+1) % MAX_MESSAGE_NUMBER
        else:
            # wait nicely
            time.sleep(0.1)
except Exception as e:
    logging.exception("program terminated",e)

# whatever happens we must do this
mqttc.loop_stop()