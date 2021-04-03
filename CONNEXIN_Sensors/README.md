# CONNEXIN SENSORS

Renamed from clarityBridge to connexinBridge to reduce confusion. The program now uses TOML config files.

The connexinBridge.py program reads the connexin sensors deployed in Hull then repackages the data and sends it to the connected humber database for inclusion on our sensor.connectedhumber.org map.

Although data is reported on the hour, the python script is now run as a systemd timed job at 15 minute intervals. 

# systemd files

## connexinBridge.timer

Script runs every 15 minutes

```
[Install]
WantedBy=timers.target
[Unit]
Description=connexinBridge Timer
StartLimitIntervalSec=0

[Timer]
OnCalendar=*-*-* *:0,15,30,45:0
Unit=connexinBridge.service


[Install]
WantedBy=timers.target


```

## connexinBridge.service

Invoked by the timer.

```
[Unit]
Description=connexinBridge service
StartLimitIntervalSec=0

[Service]
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=connexinBridge
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
RuntimeDirectoryMode=755
ExecStartPre=-/bin/mkdir /run/connexinBridge
ExecStartPre=-/bin/chown CHAdmin:CHadmin /run/connexinBridge
ExecStart=/usr/bin/env python3 /home/CHAdmin/connexinBridge.py

[Install]
WantedBy=multi-user.target
```
