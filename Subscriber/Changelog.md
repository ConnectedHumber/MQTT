# dbLoader.py Change log #

This program receives MQTT messages with a JSON payload from a broker. Messages are added to a queue of jobs and processed in the main thread.

The JSON keys MUST include a "dev" which is the unique device identifer.

Valid keys are read from the reading_value_types table when the program first runs. Additions therefore require the dbLoader daemon to be restarted.

Some shorthand aliases are also catered for such as temp=temperature, lat=latitude. The allowed aliases are listed in the TOML config file.

There are two possible timestamps. The one sent with the JSON is the date/time when the message was 'recorded on' by the device. The second is the date/time the data was 'stored on' (into the database). The Air Quality Map (https://aq.connectedhumber.org/app/) uses these timestamps to display data.

Configuration information is in dbLoader.toml, which is imported by this program as well as Shared.toml.

Incoming data is stored to a MariaDb database

## 23/02/2019 V1.00 ##
- First release

## 23/2/2019 V1.10 ##
- added sleep(0.1) to main loop to reduce cpu usage

## 25/02/2019 V1.20 ##

- Added altitude - requires extra column reading_altitude in reading_values
- Added more aliases for altitude,longitude and latitude
- Moved alias definitions to settings.py
- Altered return values from getRecordedOn() to simplify the SQL  

## 12/3/2019 V1.30 ##

- fixed problem whereby lat/lon/alt were inserted as zeros instead of NULLs
- added code to check that timestamps are not future dates - ignored if they are

## 12/3/2019 V1.31 ##

- added code to add UTC to a timestamp if the timezone is missing

## 08/02/2019 V2.00 ##
- added code to load the data types from the reading_value_types table instead of from settings.py. Chnages to 
  reading_value_types requires as restart of the dbLoader service

## 04/3/2021 V2.01 ##
- added to reconnect to the MQTT broker if, for some reason, the broker disconnects. previously we relied on keepalives.

## 04/3/2021 V2.02 ##
- corrected alias for pax_bluetooth

## 11/03/2021 V2.03 ##
- added PID file creation

## 3/4/2021 V3.00 ##
- now uses TOML configuration file
