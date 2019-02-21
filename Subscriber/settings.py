# settings.py
#
# Author: 	Brian Norman
# Date: 	19th Feb 2019
#
# place this file in the same folder as chDataLoad_JSON_Vx.xx.py
#
# this file should only be readable by root(sudo chmod 0644 should do it)
#
#
# it provides the passwords etc needed for chDataLoad_JSON_Vx.xx.py to
# connect to an MQTT broker and local database
#
# if mqttClientUser is set to None


# MQTT settings
mqttBroker = 'mqtt.connectedhumber.org'
mqttClientUser = "mqttUsername"
mqttClientPassword = "mqttPassword"
mqttTopic = "airquality/data"
mqttConnectTimeout=20 # seconds to wait for on_connect at startup
mqttKeepAlive=60		# ping will be sent if no messages have for this time

# database settings
dbHost="127.0.0.1"
dbUser="dbUsername"
dbPassword="dbPassword"
dbName="aq_db"

logFile="/var.log/aq_db.log"
