"""
devProcessor.py

Author:     Brian Norman
Date:       30/10/2019
Version:    1.0

The code uses the logging module which should be setup by the caller to log to file
see devManager.py

USAGE:

    import logging
    import Processor

    msgHandler=Processor.MsgHandler(database,debug)

    jsonReply=msgHandler.decodeJSON(msgNum,payloadJSON)

    msgNum - a sequence number to group messages in the log file (debugging help)
    payloadJSON= a utf-8 decoded MQTT message in JSON format "{.....}". See below

RETURN

    returns an un-encoded JSON string (jsonReply)

    where jsonreply has the format {"dev":DEVICE,"status":STATUS,"msg":MESSAGE}

    DEVICE

    will be the device name sent or % if no device name was sent. Returning % allows
    devices to retry if they haven't seen a valid response for their device name

    STATUS

    "failed" or "ok"

    MESSAGE

    A string explanation of the problem

msgNum is used in logging to visually identify individual calls to decodeJSON().
payloadJSON is the UTF-8 decoded payload string

It is recommended that the user uses queuing to stack MQTT message callbacks
to be processed sequentially.

Since the addition of new devices is not a flurry of activity there should be no
problem with a small queue size

The decodeJSON() validates all compulsory parts of the supplied JSON data. If any is missing the device is not
added.

Commands: (only one so far)

addNewDevice


{"cmd":"addNewDevice","name":"devname","lat":53.7,"lon":-0.34,"alt":alt,"owner":owner_json,"type": type_json,
"sensors":"BME280,SDS011"}

where type_json is  nested JSON

{ "processor":"Rpi","Connection":"WiFi","power":"USB","software":"ESPEasy","other":"self configured"}

and owner_json is nested json

{ "fname":"first_name","lname":"surname","post":"postcode","phone":"phone","email":"email address"}


NOTE: underscored methods below are not meant to be called externally (except by test programs)



"""

import json
import mysql.connector
import time
import logging
import sys


# aliases for device table fields in JSON
device_alias={
    "name":"device_name",
    "lat":"device_latitude",
    "lon":"device_longitude",
    "alt":"device_altitude",
    "owner":"owner_id",
    "type":"device_type",
    "class":"class",
    #"sensors":"sensors" not a column in devices
}

# aliases for owners table fields in JSON

owners_alias={
    "fname":"fname",
    "lname":"lname",
    "post":"postcode",
    "phone":"phone",
    "email":"email",
}

# aliases for device_types table fields in JSON

type_alias={
    "proc": "processor",
    "conn":"connection",
    "pwr":"power",
    "sw":"software",
    "other":"other"
}

type_device_sensors={
    "device_id": "device_id",
    "sensors_id":"sensors_id",
}

# optional device fields (ok if missing, replaced with NULL)
device_table_optional=["alt","owner"]

#strings to enable quick changes
CMD="cmd"
DEV="dev"
STATUS="status"
MSG="msg"
ADD_NEW_DEVICE="addNewDevice"
ADD_NEW_CLASS="addNewClass"
CLASS="class"
TYPE="type"
FNAME="fname"
LNAME="lname"
NAME="name"
OWNER="owner"
OK="ok"
SUCCESS=True
FAILED=False
DEVNAME="device_name"
SENSORS="sensors"

MAXDEVLEN=16    # only 16 characters in the database

class msgHandler:
    _mydb=None
    _debug=False

    _payloadDict=None   # the decoded JSON string

    # values extracted from JSON command
    _devInfo=None
    _typeInfo=None
    _sensorInfo=None
    _ownerInfo=None

    ##############################################################################################
    #
    # decodeJSON(msg_num,database,json_payload)
    #
    # entry point for normal use.
    #
    # used to analyse the received JSON and call the required command
    # msg_num is prepended to log output to make it easier to track individual
    # calls
    #
    # { cmd:addNewDevice,device_name: xxxxx, device_longitude: xxxxx, device_latitude:xxxxx,type:[{...}],sensors:csv}
    #
    # populates self._devInfo (dic), self._typeInfo (dic) and self._sensorInfo (list)
    # then calls the required cmd
    #
    # returns un-encoded json string with keys: dev, status and msg
    #
    #
    def decodeJSON(self,msg_num,payload):
        logging.info("")
        logging.info("%s decodeJSON(...): payload=%s", msg_num, payload)

        # reset everything
        self._devInfo = {}
        self._typeInfo = {}
        self._sensorInfo = []
        self._ownerInfo={}
        self._payLoadJson = None

        thisCmd=None
        thisDev=None

        try:
            # payload string was UTF-8 decoded when added to the job queue
            self._payloadDict = json.loads(payload)
            logging.info("%s decodeJSON(): JSON was read ok", msg_num)

            # a device name and command are compulsory
            # the device name is used by the caller
            # to identify replies to command

            payloadKeys=self._payloadDict.keys()

            # must do DEV first
            if NAME in payloadKeys:
                thisDev = self._payloadDict[NAME]

            if thisDev is None or len(thisDev) == 0:
                return self._reply(msg_num, "%",FAILED,"Missing device name")

            if len(thisDev)>MAXDEVLEN:
                return self._reply(msg_num,"%", FAILED, "Device name exceeds "+str(MAXDEVLEN)+" chars")

            if CMD in payloadKeys:
                thisCmd= self._payloadDict[CMD]

            if thisCmd is None or len(thisCmd)==0:
                return self._reply(msg_num,"%",FAILED,"Missing command")


            # we have a CMD and a DEV so...
            # process the cmd (if we know it)

            if thisCmd==ADD_NEW_DEVICE:
                status,msg=self._addNewDevice(msg_num)
                return self._reply(msg_num,thisDev,status,msg)

            elif thisCmd==ADD_NEW_CLASS:
                status,msg = self._addNewClass(msg_num)
                return self._reply(msg_num,thisDev,status,msg)

            else:
                logging.error("%s decodeJSON() Command not implemented %s",msg_num,thisCmd)
                return self._reply(msg_num,thisDev,FAILED,"Unknown command")

        except Exception as e:
            logging.exception("%s decodeJSON(): Malformed message ignored. Exception=%s",msg_num,e)
            return self._reply(msg_num,thisDev, FAILED, "Malformed JSON message ignored.")


    ################################
    #
    # _reply(dev,status,msg)
    #
    # helper for decodeJSON()
    def _reply(self,msg_num,dev,status,msg):
        reply = {
            DEV: dev,
            STATUS: status,
            MSG: msg
        }
        r=json.dumps(reply)
        logging.info("%s Reply = %s ",msg_num,r)
        return r

    #################################################################################################
    #
    # methods after here are not meant for public consumption
    #
    #################################################################################################

    # normal constructor
    def __init__(self, database, debug=False):
        assert database is not None, "Database parameter is required"
        self._mydb = database
        self._debug = debug

    ##################################################################
    #
    # input data validators for tables 'devices', 'device_types',
    # 'device_sensors' and 'owners'
    ##################################################################
    def _validateDevice(self,msg_num):
        logging.info("%s _validateDevice()",msg_num)

        # check must haves
        for key in device_alias.keys():
            if (not key in device_table_optional) and (not key in self._payloadDict):
                logging.error("%s _validateDevice(): Required device key '%s' is missing.", msg_num, key)
                return (FAILED, "Required device key '" + key + "' is missing.")

            if key in self._payloadDict.keys():
                self._devInfo[device_alias[key]] = str(self._payloadDict[key]) # mysql cannot convert lat/lon

        if self._deviceNameExists(msg_num,self._devInfo["device_name"]):
            return (FAILED, "device name already exists")

        return (SUCCESS,"device info ok")

    #----------------
    def _validateOwner(self,msg_num):
        logging.info("%s _validateOwner()", msg_num)

        if not OWNER in self._payloadDict:
            logging.info("%s _validateOwner() No owner information. Optional so ignored.")
            return (SUCCESS,"Optional owner ignored")

        # get any (optional) owner information into self._ownerInfo
        owner=self._payloadDict[OWNER]
        if (not FNAME in owner) or (not LNAME in owner):
            logging.error("%s _validateOwner() Missing fname or lname",msg_num)
            return (FAILED,"Missing fname or lname keys in owner info")

        for key in owner:
            if not key in owners_alias:
                logging.error("%s _validateOwner() Invalid owner key '%s' in json", msg_num,key)
                return (FAILED,"Invalid owner key '"+str(key)+"'")
            self._ownerInfo[owners_alias[key]]=owner[key]

        if len(self._ownerInfo[FNAME])==0 or len(self._ownerInfo[LNAME])==0:
            logging.error("%s _validateOwner() Empty fname or lname.", msg_num)
            return (FAILED, "Empty fname or lname.")

        # ownerInfo contains fname and lname at least
        return (SUCCESS,"Owner info validated ok")

    #---------------
    def _validateType(self,msg_num):
        logging.info("%s _validateType()",msg_num)
        # required for the device_types table
        if not TYPE in self._payloadDict:
            logging.error("%s decodeJSON() Missing type information.", msg_num)
            return (FAILED, "Device type info missing.")

        thisType = self._payloadDict[TYPE]

        for alias in type_alias.keys():
            if alias in thisType:
                self._typeInfo[type_alias[alias]] = thisType[alias]
            else:
                logging.error("%s _validateType() Unexpected key '%s'",msg_num,alias)
                return (FAILED,"Unexpected type key '"+alias+"' in type JSON")

        return (SUCCESS,"Type info validated ok")
        # ---------------

    def _validateClass(self, msg_num):
        logging.info("%s _validateClass()", msg_num)
        # required for the device_types table
        if not CLASS in self._payloadDict:
            logging.error("%s decodeJSON() Missing classs information.", msg_num)
            return (FAILED, "Device class info missing.")

        # validateDevice() will set _devInfo[CLASS]
        id=self._getClassId(msg_num)
        if id is None:
            return (FAILED,"Class Id not found")
        logging.info("%s _validateClass() validated ok", msg_num)
        return (SUCCESS, "Class validated ok")

    #-------------------
    def _validateSensors(self,msg_num):
        logging.info("%s _validateSensors()",msg_num)

        sensors=None

        # required for the device_sensor table
        if SENSORS in self._payloadDict:
            sensors=self._payloadDict[SENSORS]

        if sensors is None or len(sensors)==0:
            logging.error("%s _validateSensors() No sensors listed", msg_num)
            return (FAILED,"No sensors listed.")

        self._sensorInfo=sensors.split(",")  # comma seperated values

        # check ALL sensor names are valid
        for sensor in self._sensorInfo:
            if self._getSensorId(msg_num,sensor) is None:
                logging.error("%s _validateSensors() Unknown sensor '%s'", msg_num,sensor)
                return (FAILED,"Unknown sensor '"+str(sensor)+"'")

        logging.info("%s _validateSensors() validated ok", msg_num)
        return (SUCCESS,"Sensors validated ok")


    ##################################################################
    #
    # _showInfo(msg_num)
    #
    # for debugging
    #
    ##################################################################

    def _showInfo(self, msg_num):
        if not self._debug: return
        logging.info("%s showInfo().....", msg_num)
        logging.info("%s _cmd=%s", msg_num, self._payloadDict[CMD])
        logging.info("%s _devInfo :-%s", msg_num, self._devInfo)
        logging.info("%s _typeInfo :-%s", msg_num, self._typeInfo)
        logging.info("%s _sensorInfo :-%s", msg_num, self._sensorInfo)
        logging.info("%s .....showInfo()", msg_num)



    ##################################################################
    #
    # _deviceNameExists()
    #
    # returns True or False
    #
    # On error returns None and caller should abort the program
    #

    def _deviceNameExists(self, msg_num, name):

        logging.info("%s _deviceNameExists(): checking if device name (%s) is unique", msg_num, name)

        try:
            sql = 'select device_id from devices where device_name="' + str(name) + '";'

            mycursor = self._mydb.cursor()
            mycursor.execute(sql)

            r = mycursor.fetchone()
            if r is not None:
                logging.info("%s _deviceNameExists() device_id=%s", msg_num, r[0])
                return True

            logging.info("%s,_deviceNameExists() device not found", msg_num)
            return False

        except Exception as e:
            logging.error("%s _deviceNameExists(): Unable to tell if device name (%s) is unique. Exception=%s",
                          msg_num, name, e)
            return None

    ##########################################################
    #
    # _addDeviceType()
    #
    # each device has it's own type
    #
    # uses self._typeInfo
    #
    def _addDeviceType(self,msg_num):
        logging.info("%s _addDeviceType()",msg_num)

        if not self._typeInfo:
            logging.info("%s _addDeviceType() no type info.", msg_num)
            return None

        # build an SQL to add to device_types
        sql = "insert into device_types ("

        fieldList=None
        valueList=None

        for k in self._typeInfo.keys():
            if fieldList is None:
                fieldList=k
                valueList="%("+k+")s"
            else:
                fieldList=fieldList+","+k
                valueList=valueList+",%("+k+")s"

        # SQL format %(name)s is used for each parameter

        sql = sql + fieldList + ") values (" +valueList + ");"
        try:
            # add the new type record
            mycursor=self._mydb.cursor()
            mycursor.execute(sql, self._typeInfo)
            self._mydb.commit()

            # get the new type ID
            mycursor.execute("select max(device_type) from device_types;")
            r=mycursor.fetchone()
            if r is None:
                logging.error("%s _addDeviceType() max(device_type) returned None.", msg_num)
                return None # failed to insert??
            typeId=r[0]
            logging.info("%s _addDeviceType() new type id=%s",msg_num,typeId)
            return typeId

        except Exception as e:
            logging.exception("%s _addDeviceType() failed. Exception: %s",msg_num,e)
            return None

    #################################################################
    #
    # _addOwner(msg_num)
    #
    # returns Owner Id or None
    #################################################################

    def _addOwner(self,msg_num):

        logging.info("%s _addOwner()",msg_num)

        # return value is the table index (owner id)
        if len(self._ownerInfo.keys())==0:
            logging.info("%s _addOwner() No information to add. Ignored.",msg_num)
            return None

        sql="insert into owners ("
        fieldList=None
        valueList=None

        for k in self._ownerInfo.keys():
            if fieldList is None:
                fieldList=k
                valueList="%("+k+")s"
            else:
                fieldList=fieldList+","+k
                valueList=valueList+",%("+k+")s"

        # SQL format %(name)s is used for each parameter

        sql = sql + fieldList + ") values (" +valueList + "); "
        try:
            # add the owner record
            mycursor=self._mydb.cursor()
            mycursor.execute(sql, self._ownerInfo)
            self._mydb.commit()

            # get the owner_id
            mycursor.execute("select max(owner_id) from owners;")
            r=mycursor.fetchone()

            if r is None:
                logging.error("%s _addOwner() returns None for max(owner_id)",msg_num)
                return None
            owner_id=r[0]
            logging.info("%s _addOwner() returns owner_id=%s",msg_num,owner_id)
            return owner_id

        except Exception as e:
            logging.exception("%s _addOwner() failed. Exception: %s",msg_num,e)
            return None

    #################################################################
    #
    # commands called from decodeJSON() - all return (status,msg)
    #
    #################################################################
    #
    # _addNewDevice
    #
    # adds a new device.
    #
    # uses _deviceInfo,_typeInfo,_sensorInfo
    # these have been checked by decodeJSON()
    #
    def _addNewDevice(self,msg_num):

        logging.info("%s _addNewDevice()",msg_num)

        # validate the devices information
        (r, msg) = self._validateDevice(msg_num)
        if r==FAILED: return (r, msg)

        # validate the device type information
        (r, msg) = self._validateType(msg_num)
        if r==FAILED: return (r, msg)

        # validate the device Class information
        (r, msg) = self._validateClass(msg_num)
        if r==FAILED: return (r, msg)

        # validate the device sensor list
        (r, msg) = self._validateSensors(msg_num)
        if r==FAILED: return (r, msg)

        # validate any owner information
        (r, msg) = self._validateOwner(msg_num)
        if r==FAILED: return (r, msg)

        self._showInfo(msg_num)  # returns empty handed if _debug=False

        #must add to device_types table first
        device_type=self._addDeviceType(msg_num)

        if device_type is None:
            return(FAILED,"Unable to insert device type info")
        self._devInfo["device_type"]=device_type

        # now add any owner and class information
        self._devInfo["owner_id"]=self._addOwner(msg_num)

        class_id=self._getClassId(msg_num)
        if class_id is None:
            return (FAILED,"Error fetching device class id")

        self._devInfo[CLASS]=class_id

        # build an SQL for adding to devices table - return device_id
        sql = "insert into devices ("
        fieldList =None
        valueList =None
        try:
            # using named parameters
            for k in self._devInfo.keys():
                if fieldList is None:
                    fieldList=k
                    valueList="%("+k+")s"
                else:
                    fieldList=fieldList+","+k
                    valueList=valueList+",%("+k+")s"

            sql = sql + fieldList + ") values (" + valueList + ");" # "

            # insert the record
            mycursor=self._mydb.cursor()
            mycursor.execute(sql,self._devInfo)
            self._mydb.commit()

            # get back the new device id
            mycursor.execute("select max(device_id) from devices;")
            r=mycursor.fetchone()
            if r is None:
                logging.error("%s _addNewDevice() failed to return device_id",msg_num)
                return (FAILED,"Unable to add a new device")

            logging.info("%s _addNewDevice max device_id returns %s",r)
            device_id=r[0]
            logging.info("%s _addNewDevice() Returns device_id %s", msg_num,device_id)
            # finally add sensors to the device_sensors table
            (r,msg)=self._addSensors(msg_num,device_id)
            if r==FAILED: return (r,msg)
            return (SUCCESS,"Device was added ok")

        except Exception as e:
            logging.exception("%s _addNewDevice() Exception %s",msg_num,e)
            return (FAILED,"Code Exception adding new device.")

    ##############################
    #
    # _addNewClass(msg_num)
    #
    ##############################

    def _addNewClass(self, msg_num):
        logging.error("%s, _addNewClass() Not yet implemented", msg_num)
        return (FAILED, "_addNewClass() Not yet implemented")

    ##############################
    #
    # _addSensors(msg_num,device_id)
    #
    # self._sensorInfo is a list of sensors to add - already checked by decodeJSON()
    #
    # device_sensors table row is (device.device_id,sensor.id), one for each
    # sensor
    #

    def _addSensors(self, msg_num, device_id):

        logging.info("%s _addSensors() device_id=%s , sensors=%s", msg_num, device_id, self._sensorInfo)

        # use a dictionary for the SQL command
        # device_id is constant
        data = {
            "device_id": device_id,
            "sensors_id": None
        }

        mycursor = self._mydb.cursor()
        sql = 'insert into device_sensors (device_id,sensors_id) values ("%(device_id)s","%(sensors_id)s");'
        try:
            # add every sensor - all validated before this call
            for sensorName in self._sensorInfo:
                data["sensors_id"] = self._getSensorId(msg_num, sensorName)
                mycursor.execute(sql, data)
                self._mydb.commit()

            logging.info("%s _addSensors() All sensors were added.", msg_num)
            return (SUCCESS, "sensors added")

        except Exception as e:
            logging.exception("%s _addSensors(): Error adding to device_sensor table. Exception=%s", msg_num, e)
            return (FAILED, "Code exception adding sensor")

    ################################
    #
    # updateDevice
    #
    # uses self._devInfo, self._typeInfo,self.__sensorInfo

    #

    def _updateDevice(self, msg_num):
        logging.error("%s _updateDevice() not yet implemented", msg_num)
        return (FAILED, "_updateDevice() not yet implemented")

    ##############################
    #
    # _getSensorId(name)
    #
    # returns the Id of the sensor or None

    def _getSensorId(self,msg_num,name):
        sql='select id from sensors where type="'+str(name)+'";'
        try:
            mycursor = self._mydb.cursor()
            mycursor.execute(sql)
            r=mycursor.fetchone()
            if r is None: return None
            id=r[0]
            logging.info("%s _getSensorId() Found sensor name=%s id=%s",msg_num,name,id)
            return id
        except Exception as e:
            logging.error("%s _getSensorId() error unable to get id. Exception=%s",msg_num,e)
            return None


    ##############################
    #
    # _getClassid(msg_num)
    #
    # the device class name should have been validated by addNewDevice() before this is called
    #
    ##############################

    def _getClassId(self,msg_num):
        logging.info("%s _getClassId() ",msg_num)
        sql="select id from device_class where description='"+str(self._devInfo[CLASS])+"';"
        try:
            mycursor=self._mydb.cursor()
            mycursor.execute(sql)
            r=mycursor.fetchone()
            if r is None:
                logging.info("%s _getClassId() Class not found.",msg_num)
                return None
            classId=r[0]
            if self._debug: logging.info("%s _getClassId() class id=%s", msg_num, classId)
            return classId
        except Exception as e:
            logging.error("%s _getClassId() Error: Exception %s", msg_num,e)
            return None

