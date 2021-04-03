# HCC_Sensors

The program ttnHccBridge.py has been renamed hccSensorBridge.py to clarify which sensors are being monitored. The program takes readings from TTN and converts them to the JSON strings the Broker needs.

The program loops continuosly processin TTN callbacks for the HCCSENSORs

It uses the python ttn library and therefore requires python 3 in order to run.

# systemd service file #


file: /etc/systemd/system/hccSensorBridge.service
```
[Unit]
Description=HCCSENSOR Bridge
After=network-online.target
After=mosquitto-mqtt.service

[Service]
PermissionsStartOnly=True
User=CHAdmin
Group=CHAdmin
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ttnHccBridge
Restart=always
Type=simple
WorkingDirectory=/home/CHAdmin
RestartSec=3
ExecStartPre=-/bin/mkdir /run/hccSensorBridge
ExecStartPre=-/bin/chown ttnHccBridge:ttnHccBridge /run/HccSensorBridge
ExecStopPost=-/bin/rm -r /run/HccSensorBridge
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
