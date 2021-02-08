# DefraSettings.py
#
# settings used by defraBridge.py
#
#

# not used, just for reference if GNSS location is wanted.
# could be sent with JSON

location = {"UKA00450-2": (53.74878, -0.341222),
            "UKA00600-01": (53.758971, -0.305749),
            "UKA00647-01": (53.619241, -0.213324)}

# id given by defra site information.
device_id = {"Hull Freetown": "UKA00450-02",
             "Hull Holderness Road": "UKA00600-01",
             "Immingham Woodlands Avenue": "UKA00647-01"}

# note that missing sensor types just waste computer time
# comment out to improve performance

stations = {
    "Hull Freetown": {
        #3504: "CO", # gone
        2127: "SO2",
        # 267 : "SO2", # gone
        4062: "NO",
        594: "PM10",
        2126: "PM25",
        # 266 : "PM25",  # gone
        265: "O3",
        # 2125: "O3", # gone
        # 1507: "NO2", # gone
        263: "NO2",
        # 2123: "NO2", # gone
        264: "NOXasNO2",
        # 2124: "NO2" # gone
        },

    "Hull Holderness Road": {
        4063: "NO",
        268: "PM10",
        # 2539: "vPM10", # gone
        # 2538: "nvPM10", # gone
        269: "NO2",
        270: "NOXasNO2"
        },

    "Immingham Woodlands Avenue": {
        4608: "NO",
        4609: "NO2",
        4611: "NOXasNO2"}
}



main_url = "https://uk-air.defra.gov.uk/sos-ukair/api/v1/timeseries/"
append_url = "/getData?timespan="
never_seen = 14 # days ago to use for never before seen sensors