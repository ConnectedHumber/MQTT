# HCC_Sensors

The program ttnHccBridge.py has been renamed hccSensorBridge.py to clarify which sensors are being monitored. The program takes readings from TTN and converts them to the JSON strings the Broker needs.

The program loops continuosly processing TTN callbacks for the HCCSENSORs

It uses the python ttn library and therefore requires python 3 in order to run.

# systemd service file #


file: /etc/systemd/system/hccSensorBridge.service
```
[Unit]
Description=HCC Sensor Bridge
After=network-online.target
After=mosquitto-mqtt.service

[Service]
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=hccSensorBridge
Restart=always
Type=simple
WorkingDirectory=/home/CHAdmin
RestartSec=3
ExecStartPre=-/bin/mkdir /run/hccSensorBridge
ExecStartPre=-/bin/chown CHAdmin:CHAdmin /run/hccSensorBridge
ExecStopPost=-/bin/rm -r /run/hccSensorBridge
ExecStart=/usr/bin/python3 /home/CHAdmin/hccSensorBridge.py

[Install]
WantedBy=multi-user.target
```
# log rotate #

file: /etc/logrotate.d/HccSensorBridge
```
/var/log/ttnHccBridge/HccSensorBridge.log{
missingok
notifyisempty
size 50k
daily
compress
maxage 30
rotate 10
create 0644 CHAdmin CHAdmin
copytruncate
}
```
