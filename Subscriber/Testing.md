
# Test Procedures #

Testing should be done in two stages: 'Local Only' and 'Live with local DB'

You need a Linux machine with mysql and python.

Check the python import statements in chDataLoad_JSON_Vx.xx.py and make sure these are installed- preferably globally. Most are standard.

```
import paho.mqtt.client as paho
from dateutil.parser import *
import mysql.connector
import time
import json
import copy
import logging
import sys
```

The SQL to create the database is in the database folder above.

You will need to install mosquitto MQTT broker (sudo apt-get install mosquitto)

You need to download: settings.py and chDataLoad_JSON_Vx_xx.py - use the latest.

## Local Only ##

Edit settings.py and put in your local database/mqtt broker usernames and passwords

Create a log file folder aq_db in /var/log and set the logFile entry to /var/log/aq_db/mqtt.log

Add a new text document in /etc/logrotate.d

```
/var/log/aq_db/mqtt.log{
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

Now you can launch the subscriber
```
sudo python chDataLoad_JSON_Vx_xx.py &
```

## Live with local DB ##

All you need to do here is change the settings file so that it connects with the connectedhumber mqtt broker. Details available to connectedhumber members on request 

If the subscriber program works for a few hours, without error then it is good to go live and should be copied to the live server. Kill the current running subscriber then launch the new version.
