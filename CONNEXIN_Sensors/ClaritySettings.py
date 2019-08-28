# setting for the clarityBridge.py
#
# these are devices deployed by connexin
#

logFile="/var/log/clarityBridge.log"
lastTimestampFile="/home/CHAdmin/clarityTimestamp.txt"

api_key = '<ASK>'
base_url="https://clarity-data-api.clarity.io/v1"

mqttBroker = '51.140.15.143'     #'mqtt.connectedhumber.org'
mqttClientUser = "connectedhumber"
mqttClientPassword="<ASK>"
mqttTopic = "airquality/data"
mqttConnectTimeout=20	# only checked on startup
mqttKeepAlive=60		# client pings server if no messages have been sent in this time period.
mqttPublishTimeout=30   # return an error if it takes this long
mqttDisconnectTimeout=10# as above

# definitions to avoid spelling errors
LOCATION='location'
COORDS='coordinates'
MEASURES='characteristics'
VALUE="value"
ID="_id"
DEVCODE='deviceCode'    # used for CH 'dev' param
TIME='time'             # timestamp
DEVPREFIX="CL-"
LONGITUDE='longitude'
LATITUDE='latitude'
TIMESTAMP="timestamp"


# alias Clarity measurement keys to CH keys
# CASE SENSITIVE
# unused keys have values of None - they will
# be ignored to reduce size of JSON publish
# see addKeyValue()

aliases={}
aliases["relHumid"]="humidity"
aliases["temperature"]="temp"
aliases["pm2_5ConcMass"]="PM25"
aliases["pm2_5ConcNum"]=None       # not used
aliases["pm1ConcMass"]=None
aliases["pm1ConcNum"]=None       # not used
aliases["pm10ConcMass"]="PM10"
aliases["pm10ConcNum"]=None       # not used
aliases["no2Conc"]="NO2"
aliases["vocCons"]="VOC"
aliases["co2Conc"]="CO2"
aliases[TIME]=TIMESTAMP
aliases[DEVCODE]='dev'
aliases[LONGITUDE]=LONGITUDE
aliases[LATITUDE]=LATITUDE
aliases[ID]=None
