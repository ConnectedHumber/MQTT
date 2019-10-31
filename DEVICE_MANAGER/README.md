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
