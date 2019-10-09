# DEFRA Sensors

Python code to download readings from a defra sensor, repackage it and send it to our MQTT broker.

The code is run from a root crontab (needs to be able to write to the logfile in /var/log) every 15 minutes past the hour.

It records the timestamp of the last reading ( in ~/defraTimestamp.txt )to ensure it doesn't duplicate readings. Only new readings are sent to the broker.

The DEFRA readings are updated approximately once per hour.
