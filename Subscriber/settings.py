# settings.py
#
# Author: 	Brian Norman
# Date: 	23rd Feb 2019
#
# place this file in the same folder as dbLoader.py
#
# this file should only be readable by root(sudo chmod 0644 should do it)
#
#
# it provides the passwords etc needed for dbLoader.py to
# connect to an MQTT broker and local database
#
# if mqttClientUser is set to None authentication is not used
# but the broker must accept conenctions without it


# MQTT settings
mqttBroker = 'mqtt.connectedhumber.org'
mqttClientUser = "mqttClientUser"
mqttClientPassword = "mqttClientPassword"
mqttTopic = "airquality/data"
mqttConnectTimeout=20	# only checked on startup
mqttKeepAlive=60		# client pings server if no messages have been sent in this time period.


# database settings
dbHost="127.0.0.1"
dbUser="dbUser"
dbPassword="dbPassword"
dbName="aq_db"

# LOGGING
logFile="/var/log/aq_db.log"

MAX_MESSAGE_NUMBER=9999
MAX_JOBS=100