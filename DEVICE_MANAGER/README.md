# DEVICE MANAGER

Code to enable a device to register with the sensors database automatically.

The sensor device sends a JSON string to the broker on the topic devmgr/install and receives and acknowledgement via the topic devmgr/reply.

devManager.py subscribes to devmgr/install and passes messages to devProcessor.py's msgHandler class. the msgHandler returns the reply to devManager which then publishes it on the topic devmgr/reply.

The device id is returned in the reply so that devices can identify replies they are listening for.

The python scripts detail the message formats.

The code is intended to be run as a system task unser systemctl control. The service info file devManager.service should be located at
in /etc/systemd/service.

```
[Unit]
Description=devManager service
After=mysqld.service

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
ExecStart=/usr/bin/env python /home/pi/aq_db/devManager.py

[Install]
WantedBy=multi-user.target
```

devManager.py creates a log file /var/log/devManager.log which should be added to logrotate by creating a file /etc/logrotate.d/devManager which contains :-
```

/var/log/devManager.log{
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

The service can then be started with:-
```
sudo systemctl enable devManager
sudo systemctl start devManager
systemctl status devManager
```

The first line enables the service to be restarted on boot and/or failure. You will be asked for the root password (the service runs as root so it can create the log files).
The second line actually starts it.
The third line gives a nice warm glow if it says it's running.

# DEVICE CHECKER
This program now runs from a systemd timer at midnight every day and checks if a device has been sending data recently.

If last_seen is 31 days, or more, old then the visible flag is set to 0. 

The dbLoader program (from V2.04) will set visible=1 (devices table) as soon as new data is seen thus quickly making the sensor visible on the sensor map again.

## DevChecker.timer

The timer needs to be enabled to run on boot up and started.
```
[Unit]
Description=devChecker Timer
StartLimitIntervalSec=0

[Timer]
OnCalendar=*-*-* 0:0:0
Unit=DevChecker.service


[Install]
WantedBy=timers.target

```
## DevChecker.service

The service does not need to be enabled and should only be started from the timer BUT for testing it could be started as it will terminate when its work is done.

```
[Unit]
Description=devChecker service
StartLimitIntervalSec=0

[Service]
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=DevChecker
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
RuntimeDirectoryMode=755
ExecStartPre=-/bin/mkdir /run/DevChecker
ExecStartPre=-/bin/chown CHAdmin:CHadmin /run/DevChecker
ExecStart=/usr/bin/env python /home/CHAdmin/DevChecker.py

[Install]
WantedBy=timers.target


```
