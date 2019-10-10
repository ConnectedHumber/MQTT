# DEFRA API

Data is returned in JSON strings.

## List Defra Stations

```
https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations
```

Locate the station of interest and get its {ID}

## Find the available timeseries for that {ID}

```
https://uk-air.defra.gov.uk/sos-ukair/api/v1/stations/{ID} 
```

## Getting ALL the timeseries data
```
https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/{ID}/getData?force_latest_values=true
```
## To get data between two dates

Here you tell the API the end date and the timespan. Setting the end date to tomorrow and the span to 1 day gets all of todays results.
```
https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/{ID}/getData?timespan={SPAN}/{ENDDATE}
```

{SPAN} can be P*n*D where *n* is the number of days to return

{ENDDATE}	format is yyyy-mm-dd
