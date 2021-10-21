# HCC_Sensors

The program ttnHccBridge.py has been renamed hccSensorBridge.py to clarify which sensors are being monitored. The program takes readings from TTN and converts them to the JSON strings the Broker needs.

The program loops continuosly processing TTN callbacks for the HCCSENSORs

Prior to V4.00 the code uses the python ttn library. Thereafter it uses MQTT to download uplinks.

Changes to the JSON with the TTN Stack (v3) mean that this code required numerous changes to JSON keys. After December 1st 2021 this will be academic since TTN V2 will no longer be operational. 

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
ExecStartPre=-/bin/mkdir /var/log//hccSensorBridge
ExecStartPre=-/bin/chown CHAdmin:CHAdmin /var/log/hccSensorBridge
ExecStopPost=-/bin/rm -r /run/hccSensorBridge
ExecStart=/usr/bin/python3 /home/CHAdmin/hccSensorBridge.py

[Install]
WantedBy=multi-user.target
```
# log rotate #

file: /etc/logrotate.d/hccSensorBridge
```
/var/log/hccSensorBridge/hccSensorBridge.log{
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
