# This folder contains python 3.x subscriber code #

It subscribes to the connectedhumber MQTT broker listening for messages on the topic airquality/data. When it receives a message it analyses the payload and, possibly,adds records to the database.

The data is presented on an air quality map here: https://aq.connectedhumber.org/app/

Note passwords and user names have been removed from the code.

The expected payload is a JSON string similar to this:-

```
{"dev":"devname","temp":25.4,"PM25":15.8,"PM10":10.1,"humidity":60.0,"pressure":1024.00,"timestamp":"YYY-MM-DD HH:MM:SS"}
```

All except "dev" are optional but it is pointless to send no data. The device name must be registered otherwise messages are logged and ignored. Capitalisation matters.

Note that the subscriber code sets a 'storedon' timestamp in the database as well as the timestamp included in the payload, if any. 

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




We politely request that messages are not sent to the broker more than once every 6 minutes. This gives us a 10 samples per hour view of the environment.

