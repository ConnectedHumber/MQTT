# settings.py
#
# Author: 	Brian Norman
# Date: 	25rd Feb 2019
#
# place this file in the same folder as dbLoader.py
#
# dbLoader.py should not be edited
#
# this file should only be readable by root(sudo chmod 0644 should do it)
#
#
# it provides the passwords etc needed for dbLoader.py to
# connect to an MQTT broker and local database
#

# MQTT settings
# if mqttClientUser is set to None authentication is not used
# but the broker must accept conenctions without it

mqttBroker = '<mqttBroker>'                 #replace with your MQTT broker login details
mqttClientUser = "<mqttClientUser>"
mqttClientPassword = "<mqttClientPassword>"
mqttTopic = "airquality/data"
mqttConnectTimeout=20	# only checked on startup
mqttKeepAlive=60		# client pings server if no messages have been sent in this time period.


# database settings
dbHost="127.0.0.1"
dbUser="<dbUser>"         # replace with your database login info
dbPassword="<dbPassword>"
dbName="aq_db"

# LOGGING
logFile="/var/log/dbLoader.log"

# GNSS position key aliases
# case sensitive
LATITUDE="latitude"
LONGITUDE="longitude"
ALTITUDE="altitude"

GNSS_Aliases={}
GNSS_Aliases["lon"]=LONGITUDE
GNSS_Aliases["long"]=LONGITUDE
GNSS_Aliases["longitude"]=LONGITUDE
GNSS_Aliases["lat"]=LATITUDE
GNSS_Aliases["latitude"]=LATITUDE
GNSS_Aliases["altitude"]=ALTITUDE	# currently not stored
GNSS_Aliases["alt"]=ALTITUDE

# misc
MAX_MESSAGE_NUMBER=9999
MAX_JOBS=100
