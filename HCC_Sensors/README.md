# HCC_Sensors

The program ttnHccBridge.py takes readings from TTN and converts them to the JSON strings the Broker needs.

It uses the python ttn library and therefore requires python 3 in order to run.

# systemd service file #

file: /etc/systemd/system/ttnHccBridge.service

[Unit]
Description=TTN-HCC Bridge
After=network-online.target
After=mosquitto-mqtt.service

[Service]
PermissionsStartOnly=True
User=ttnHccBridge
Group=ttnHccBridge
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ttnHccBridge
Restart=always
Type=simple
WorkingDirectory=/home/CHAdmin
RestartSec=3
ExecStartPre=-/bin/mkdir /run/ttnHccBridge
ExecStartPre=-/bin/chown ttnHccBridge:ttnHccBridge /run/ttnHccBridge
ExecStopPost=-/bin/rm -r /run/ttnHccBridge
ExecStart=/usr/bin/python3 /home/CHAdmin/ttnHccBridge.py

[Install]
WantedBy=multi-user.target

# log rotate #

file: /etc/logrotate.d/ttnHccBridge

/var/log/ttnHccBridge/ttnHccBridge.log{
missingok
notifyisempty
size 50k
daily
compress
maxage 30
rotate 10
create 0644 root root
copytruncate
}
