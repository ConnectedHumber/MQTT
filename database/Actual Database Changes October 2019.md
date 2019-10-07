# Actual Database Changes for V4 (October 2019)

## Add device_class table and initial values
```
create table device_class (id int(11) primary key not null auto_increment,description varchar(100));
insert into device_class (description) values ("Environment Sensor");
insert into device_class (description) values ("PAX Counter");
```

## Link devices table to device_class table
```
alter table devices add column class int(11) default 1;
alter table devices add constraint fk_class foreign key (class) references device_class(id);
```

## Extra reading_value_types for PAX counter
```
insert into reading_value_types (short_descr,friendly_text) values ("PAX Wifi","PAX counter Wifi hits");
insert into reading_value_types (short_descr,friendly_text) values ("PAX Bluetooth","PAX counter Bluetooth hits");
insert into reading_value_types (short_descr,friendly_text) values ("PAX RSSI","PAX counter WiFi RSSI");
```

