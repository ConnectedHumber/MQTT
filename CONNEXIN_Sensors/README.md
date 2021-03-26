# CONNEXIN SENSORS

The clarityBridge.py program reads the connexin sensors deployed in Hull repackages the data and sends it to the connected humber database for inclusion on our sensor.connectedhumber.org map.

Although data is reported on the hour, the python script is now run as a systemd timed job at 15 minute intervals. 

# systemd files

## claritybridge.timer

Script runs every 15 minutes

```
[Install]
WantedBy=timers.target
[Unit]
Description=clarityBridge Timer
StartLimitIntervalSec=0

[Timer]
OnCalendar=*-*-* *:0,15,30,45:0
Unit=clarityBridge.service


[Install]
WantedBy=timers.target


```

## clarityBridge.service

Invoked by the timer.

```
[Unit]
Description=clarityBridge service
StartLimitIntervalSec=0

[Service]
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=clarityBridge
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
RuntimeDirectoryMode=755
ExecStartPre=-/bin/mkdir /run/clarityBridge
ExecStartPre=-/bin/chown CHAdmin:CHadmin /run/clarityBridge
ExecStart=/usr/bin/env python3 /home/CHAdmin/clarityBridge.py

[Install]
WantedBy=timers.target

```
