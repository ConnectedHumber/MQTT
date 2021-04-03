# DEFRA Sensors

Python code to download readings from a defra sensor, repackage it and send it to our MQTT broker.

The code is run periodically by a systemd timer.

It records the timestamp of the last reading ( in ~/defraTimestamp.txt )to ensure it doesn't duplicate readings. Only new readings are sent to the broker.


# Systemd files

defrabridge now runs from a systemd timer instead of cron. In addition the following folders have also been created:-

/run/defraBridge

/var/log/defraBridge

## defraBridge.timer

Set to run at 30 minutes past the hour

```
[Unit]
Description=defraBridge Timer
StartLimitIntervalSec=0

[Timer]
OnCalendar=*-*-* *:30:0
Unit=defraBridge.service

[Install]
WantedBy=timers.target
```

## defraBridge.service
```
[Unit]
Description=defraBridge service
StartLimitIntervalSec=0

[Service]
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=defraBridge
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
RuntimeDirectoryMode=755
ExecStartPre=-/bin/mkdir /run/defraBridge
ExecStartPre=-/bin/chown CHAdmin:CHadmin /run/defraBridge
ExecStart=/usr/bin/env python3 /home/CHAdmin/defraBridge.py

[Install]
WantedBy=multi-user.target
```
