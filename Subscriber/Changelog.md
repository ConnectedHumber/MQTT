# dbLoader.py Change log #

This program receives MQTT messages with a JSON payload from a broker. Messages are added to a queue of jobs and processed in the main thread.

The JSON keys MUST include a "dev" which is the unique device identifer.

Other valid keys are: "timestamp", "temp", "humidity", "pressure", "PM10", "PM25","long","lat"

There are two possible timestamps. The one sent with the JSON is the date/time when the message was 'recorded on'
by the device. The second is the date/time the data was 'stored on' (into the database). The Air Quality Map
 https://aq.connectedhumber.org/app/ uses these timestamps to display data.

Configuration information is in settings.py which is imported by this program.

Incoming data is stored to a MariaDb database on Soekris

## 23/02/2019 V1.0 First release

