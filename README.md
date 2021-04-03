# MQTT
All things related to our MQTT broker and database

## Changes afoot

I am changing the programs to use TOML configuration files. All programs will be versioned at V3.00 to clarify when the change has taken place.

There will be a shared config file called Shared.toml. This will contain the MQTT and DATABASE configuration information. Some programs, like dbLoader uses MQTT and a database whilst other porgrams use one or the other.

Each program will also have it's own TOML file for program specific config data.

The programs have been recoded at the beginning to read the TOML files and assign values to local variables in a try-except so that missing values can be caught before the programs run. This will give some additional coding consistency which should make it easier for anyone wishing to read the code.
