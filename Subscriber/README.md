# This folder contains python 2.7/3.x subscriber code dbLoader.py

dbLoader.py subscribes to the connectedhumber MQTT broker listening for messages on the topic airquality/data. When it receives a message it analyses the payload and, possibly,adds records to the database.

The data is presented on an air quality map here: https://aq.connectedhumber.org/app/

Note passwords and user names have been removed from the code.

The expected payload is a JSON string similar to this:-

```
{"dev":"devname","temp":25.4,"PM25":15.8,"PM10":10.1,"humidity":60.0,"pressure":1024.00,"timestamp":"YYY-MM-DD HH:MM:SS"}
```

## JSON keys supported ##

These are listed in the settings.py file in the dictionaries GNSS_aliases and Types_id

Warning: Types_id key values MUST NOT be changed - they are tied directly to the reading_value_types database table id column.

```
dev: compulsory, e.g. CHASN-dddddd-1 (see technical meeting notes) 
temp/temperature
humidity
pressure
PM10
PM25
lat/latitude
lon/long/longitude
alt/altitude
timestamp

```


All except "dev" are optional but it is pointless to send no data. The device name must be registered otherwise messages are logged and ignored.

All keys are case sensitive.

Any JSON keys sent which are not listed above are ignored.

## About timestamps

It was agreed that we would standardise on the format YYYY-MM-DDTHH:MM:SS+nnnn

Note that the subscriber code always sets a 'storedon' (date&time received in UTC) timestamp in the database as well as the timestamp included in the payload, if any. The Air-Quality-Map uses the timestamp sent, if present, otherwise it uses the storedon timestamp.

Timestamps sent without a timezone offset are assumed to be UTC +0000.

If the timestamp sent is a future date it is ignored.

The code will actually accept a wide variety of timestamp formats. See the Python dateutil module for further information.


## Message Logging

The code uses the python logging module to record message processing. The host system should add an entry to the /etc/logrotate.d folder. something like:-

```
<abs path to logfile>{
missingok
notifyempty
size 50k
daily
compress
maxage 30
rotate 10
create 0644 root root
copytruncate
}
```


## Message Rate

We politely request that messages are not sent to the broker more than once every 6 minutes. This gives us a 10 samples per hour view of the environment.

## NOTE

chDataLoad..py are depracated. They process the JSON within the callback.The newer dbLoader.py uses job queuing and processes the payload in the main thread.
