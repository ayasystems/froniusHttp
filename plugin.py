# Fronius http python plugin
# @2020
# Author: EA4GKQ
# https://github.com/akleber/fronius-json-tools
# 06/05/2020
# - Añadido dummy con valor medio de Grid de las últimas 30 muestras
# - Mejorada reconexión automática
"""
<plugin key="FroniusHttp" name="Fronius http" author="EA4GKQ" version="1.0.3"
wikilink="https://github.com/ayasystems/froniusHttp"
externallink="https://www.fronius.com">
    <description>
        <h2>Fronius HTTP Pluging</h2><br/>
        <h3>by @ea4gkq</h3><br/>
        <a href="https://domotuto.com/fronius_domoticz_plugin/">https://domotuto.com/fronius_domoticz_plugin/</a><br/>
    </description>
    <params>
        <param field="Address" label="Fronius IP" width="200px" required="true" default="192.168.1.xx"/>
        <param field="Mode1" label="Protocol" width="75px">
            <options>
                <option label="HTTP" value="80"  default="true" />
                <option label="HTTPS" value="443"  default="true" />
            </options>
        </param>
        <param field="Mode2" label="Update speed" width="75px">
            <options>
                <option label="Normal" value="Normal"/>
                <option label="High" value="High"  default="true" />
            </options>
        </param>
        <param field="Mode3" label="Inverter model" width="150px">
            <options>
                <option label="Fronius AKU" value="Fronius6"  default="true" />
                <option label="Fronius" value="Fronius3"/>
            </options>
        </param>           
        <param field="Mode6" label="Debug" width="150px">
            <options>
                <option label="None" value="0"  default="true" />
                <option label="Python Only" value="2"/>
                <option label="Basic Debugging" value="62"/>
                <option label="Basic+Messages" value="126"/>
                <option label="Connections Only" value="16"/>
                <option label="Connections+Queue" value="144"/>
                <option label="All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>  
"""
errmsg = ""
try:
    import Domoticz
except ImportError as imperr:
    errmsg += "Domoticz import error: " + str(imperr)
try:
    import json
except ImportError as imperr:
    errmsg += " Json import error: " + str(imperr)
try:
    import time
except ImportError as imperr:
    errmsg += " time import error: " + str(imperr)
try:
    import re
except ImportError as imperr:
    errmsg += " re import error: " + str(imperr)

from functools import reduce
from enum import Enum, auto


class FroniusHttp:
    # Connection members
    ipaddress = ""
    port = 80
    sProtocol = "HTTP"
    connection = None
    interval = 1
    disconnectCount = 0

    class Model(Enum):
        FRONIUS3 = auto()
        FRONIUS6 = auto()

    model = Model.FRONIUS3

    LEDColor = 0
    ErrorCode = ""

    DAY_ENERGY = ""
    PAC = ""
    TOTAL_ENERGY = ""
    P_PV = ""  # Instant production
    E_Day = ""  # Day production
    E_Total = ""  # Total production
    E_Year = ""  # Yearly production
    P_Grid = ""  # Negative injects Positive consumes
    P_Load = ""  # Grid + solar consumption
    GRID_W = ""
    listGrid = []
    maxGridList = 30
    avgGrid = 0
    URL1 = "/solar_api/v1/GetMeterRealtimeData.cgi?Scope=System" #TODO is it used? will be overwritten in next line
    URL1 = "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
    URL2 = "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"
    # 192.168.1.51/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData&DeviceId=1

    # support for Fronius3.0-1 without Battery
    URL4 = "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=CommonInverterData"
    PAC = ""
    UAC = ""  # Grid + solar consumption
    FAC = ""
    IAC = ""
    IDC = ""
    UDC = ""
    UAC = ""
    # End-Fronius3

    current = ""

    def __init__(self):
        return

    def onStart(self):
        Domoticz.Debug("onStart")
        if errmsg:
            Domoticz.Error("Your Domoticz Python environment is not functional! " + errmsg)
            return

        try:
            self.debug_lvl = int(Parameters["Mode6"])
            if self.debug_lvl != 0:
                Domoticz.Log(f"Debug set to level: {self.debug_lvl}")
                Domoticz.Debugging(self.debug_lvl)
                DumpConfigToLog()

            self.set_model(Parameters["Mode3"].strip())

            self.ipaddress = Parameters["Address"].strip()
            self.port = int(Parameters["Mode1"].strip())
            Domoticz.Log(f"Address: {self.ipaddress}:{self.port}")
            if self.port == 443:
                self.sProtocol = "HTTPS"

            if Parameters["Mode2"].strip() == "High":
                Domoticz.Heartbeat(1)
            self.connect()

        except Exception as e:
            Domoticz.Error("onStart error: " + str(e))

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if Status != 0:
            Domoticz.Log(f"Failed to connect ({Status}) to: {self.ipaddress}:{self.port} with error: {Description}")
            return

        Domoticz.Log("Fronius connected successfully.")
        self.update_url()

    def onMessage(self, Connection, Data):
        DumpHTTPResponseToLog(Data)

        status = int(Data["Status"])

        if status == 200:
            Domoticz.Debug("Good Response received from Fronius, Disconnecting.")
            self.processResponse(self, Data)

        elif status == 302:
            Domoticz.Log("Fronius returned a Page Moved Error.")
            Connection.Send(self.format_data_response(Data["Headers"]["Location"]))
        else:
            # Handle errors
            self.connection.Disconnect()
            self.connection = None

            if status == 400:
                Domoticz.Error("Fronius returned a Bad Request Error.")
            elif status == 500:
                Domoticz.Error("Fronius returned a Server Error.")
            else:
                Domoticz.Debug("Fronius returned a status: " + str(status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug(f"onCommand called for Unit: {Unit}, Command: {Command}, Level: {Level}.")

    def onDisconnect(self, Connection):
        Domoticz.Debug(f"onDisconnect called for connection: {Connection.Address}:{Connection.Port}.")
        self.connect()

    def onHeartbeat(self):
        if self.connection is not None and self.connection.Connected():
            self.connection.Send(self.format_data_response(self.current))
        else:
            Domoticz.Debug("onHeartbeat called, Connection is down.")

    @staticmethod
    def get_devices_names_to_ids():
        name_to_unit_dict = {}
        last_unit = 0
        for unit, dev in enumerate(Devices):
            # get last unit id taken
            if last_unit < unit:
                last_unit = unit

            # create name unit mapping
            name_to_unit_dict[dev.name] = unit

        return name_to_unit_dict, last_unit

    def create_devices(self):
        self.name_to_unit_dict, last_unit = FroniusHttp.get_devices_names_to_ids()

        dev_name_list = []
        if self.model == FroniusHttp.Model.FRONIUS3:
            # Generate and extend list of devices name and subtypes
            dev_name_list += [
                # Name, Subtype
                ("F_IDC", 23),  # amper
                ("F_IAC", 23),  # amper
                ("F_FAC", 31),  # custom
                ("F_UAC", 8),   # voltage
                ("F_UDC", 8),   # voltage
                ("F_PAC", 29)]

        elif self.model == FroniusHttp.Model.FRONIUS6:
            # Generate and extend list of devices name and subtypes
            dev_name_list += [
                # Name, Subtype
                ("FROM_GRID", 29),
                ("TO_GRID", 29),
                ("HOME_LOAD", 29),
                ("FV_POWER", 29)]

        # Check and create all devices
        for dev_tuple in dev_name_list:
            name = dev_tuple[0]
            subtype = dev_tuple[0]
            if name not in self.name_to_unit_dict:
                last_unit += 1
                Domoticz.Device(Name=name, Unit=last_unit,
                                Type=243, Subtype=subtype, Switchtype=0,
                                Used=1, DeviceID=name).Create()

        # Custom device for FRONIUS6
        # TODO it can be simplified
        if self.model == FroniusHttp.Model.FRONIUS6:
            name = "AVGGRID"
            if name not in self.name_to_unit_dict:
                last_unit += 1
                Domoticz.Device(Name=name, Unit=last_unit,
                                TypeName='Custom', Options={"Custom": "1;w"},
                                Used=1, DeviceID=name).Create()

        # Update mapping
        self.name_to_unit_dict, last_unit = FroniusHttp.get_devices_names_to_ids()

    def set_model(self, model_name):
        Domoticz.Log(f"Model {model_name} selected. Creating devices.")
        # Default model is FRONIUS3 so check only if different.
        if model_name == "Fronius6":
            self.model = FroniusHttp.Model.FRONIUS6

        self.create_devices()

    def update_url(self):
        if self.model == FroniusHttp.Model.FRONIUS3:
            self.current = self.URL4
            Domoticz.Debug("onConnect.#self.current: " + self.current)
        if self.model == FroniusHttp.Model.FRONIUS6:
            self.current = self.URL1
            Domoticz.Debug("onConnect.#self.current: " + self.current)

    def format_data_response(self, url):
        return {
            'Verb': 'GET',
            'URL': url,
            'Headers': {
                'Content-Type': 'text/xml; charset=utf-8',
                'Connection': 'keep-alive',
                'Accept': 'Content-Type: text/html; charset=UTF-8',
                'Host': f"{self.ipaddress}:{self.port}",
                'User-Agent': 'Domoticz/1.0'
            }
        }

    def connect(self):
        if self.connection is None:
            self.connection = Domoticz.Connection(Name=f"{self.sProtocol}://{self.ipaddress} - Main",
                                                  Transport="TCP/IP",
                                                  Protocol=self.sProtocol,
                                                  Address=self.ipaddress, Port=self.port)
        self.connection.Connect()

    def average(self):
        if len(self.listGrid) > self.maxGridList:
            self.listGrid.pop(0)
        Domoticz.Log("List values: " + str(self.listGrid))
        self.avgGrid = reduce(lambda a, b: a + b, self.listGrid) / len(self.listGrid)
        self.avgGrid = round(self.avgGrid, 0)

    def processResponse(self, httpResp):
        stringData = httpResp["Data"].decode("utf-8", "ignore")
        data_dict = json.loads(stringData)

        if "Body" not in data_dict:
            Domoticz.Error("No Body in response")
            return

        data = data_dict["Body"]

        if "Data" not in data:
            Domoticz.Error("No Data in response")
            return

        data = data_dict["Body"]["Data"]

        self.ErrorCode = data.get('DeviceStatus', {}).get('ErrorCode', defaul="")
        if self.ErrorCode:
            Domoticz.Log(f"ErrorCode.processResponse: {self.ErrorCode}")

        self.LEDColor = int(data.get('DeviceStatus', {}).get('LEDColor', defaul=2))
        Domoticz.Log(f"LEDColor.processResponse: {self.LEDColor}")

        self.update_url()

        if self.model == FroniusHttp.Model.FRONIUS3:
            self.E_Day = get_val(data, "DAY_ENERGY")
            self.E_Total = get_val(data, "TOTAL_ENERGY")
            self.E_Year = get_val(data, "YEAR_ENERGY")
            self.PAC = get_val(data, "PAC")
            self.UAC = get_val(data, "UAC")
            self.UDC = get_val(data, "UDC")
            self.IAC = get_val(data, "IAC")
            self.IDC = get_val(data, "IDC")
            self.FAC = get_val(data, "FAC")
            instantaneoFV = self.PAC
            acumuladoKwhFV = self.E_Total  # accumulated

            Domoticz.Debug("self.PAC.processResponse.URL4  : " + str(self.PAC))
            Domoticz.Debug("self.E_Day.processResponse.URL4 : " + str(self.E_Day))

            if self.debug_lvl == -1:
                Domoticz.Error("F_PAC: " + self.PAC)
                Domoticz.Error("E_Day: " + self.E_Day)
                Domoticz.Error("E_Total: " + self.E_Total)
                Domoticz.Error("E_Year: " + self.E_Year)
                Domoticz.Error("F_UAC: " + self.UAC)
                Domoticz.Error("F_UDC: " + self.UDC)
                Domoticz.Error("F_IAC: " + self.IAC)
                Domoticz.Error("F_IDC: " + self.IDC)
                Domoticz.Error("F_FAC: " + self.FAC)

            UpdateDevice(self.name_to_unit_dict["F_PAC"], 0, instantaneoFV + ";" + acumuladoKwhFV)
            UpdateDevice(self.name_to_unit_dict["F_UAC"], 0, self.UAC + ";0")
            UpdateDevice(self.name_to_unit_dict["F_UDC"], 0, self.UDC + ";0")
            UpdateDevice(self.name_to_unit_dict["F_FAC"], 0, self.FAC + ";0")
            UpdateDevice(self.name_to_unit_dict["F_IAC"], 0, self.IAC + ";0")
            UpdateDevice(self.name_to_unit_dict["F_IDC"], 0, self.IDC + ";0")

        elif self.model == FroniusHttp.Model.FRONIUS6:
            if data['Site']['P_PV'] == 'null':
                self.P_PV = "0"
            else:
                self.P_PV = str(data['Site']['P_PV'])
            self.E_Day = str(data['Site']['E_Day'])
            self.E_Total = str(data['Site']['E_Total'])
            self.E_Year = str(data['Site']['E_Year'])
            self.P_Grid = str(data['Site']['P_Grid'])
            self.P_Load = str(data['Site']['P_Load'] * -1)
            TO_GRID = data['Site']['P_Grid'] * -1
            FROM_GRID = data['Site']['P_Grid']
            # self.P_PV     =  str(data['Site']['P_PV'])
            self.listGrid.append(FROM_GRID)
            self.average()

            if self.debug_lvl == -1:
                Domoticz.Error("P_PV: " + self.P_PV)
                Domoticz.Error("E_Day: " + self.E_Day)
                Domoticz.Error("E_Total: " + self.E_Total)
                Domoticz.Error("E_Year: " + self.E_Year)
                Domoticz.Error("P_Grid: " + self.P_Grid)  ##
                Domoticz.Error("P_Load: " + self.P_Load)  ##
                Domoticz.Error("List: " + str(self.listGrid))
                Domoticz.Error("AVG Grid: " + str(round(self.avgGrid, 0)))

            instantaneoFV = self.P_PV
            acumuladoKwhFV = self.E_Total  # accumulated

            if FROM_GRID >= 0:
                UpdateDevice(self.name_to_unit_dict["TO_GRID"], 0, "0;0")
                UpdateDevice(self.name_to_unit_dict["FROM_GRID"], 0, str(FROM_GRID) + ";0")
            if TO_GRID > 0:
                UpdateDevice(self.name_to_unit_dict["TO_GRID"], 0, str(TO_GRID) + ";0")
                UpdateDevice(self.name_to_unit_dict["FROM_GRID"], 0, "0;0")
            UpdateDevice(self.name_to_unit_dict["FV_POWER"], 0, instantaneoFV + ";" + acumuladoKwhFV)
            UpdateDevice(self.name_to_unit_dict["HOME_LOAD"], 0, self.P_Load + ";0")
            UpdateDevice(self.name_to_unit_dict["AVGGRID"], 0, self.avgGrid)


global _plugin
_plugin = FroniusHttp()


def onStart():
    global _plugin
    _plugin.onStart()


def onStop():
    global _plugin
    _plugin.onStop()


def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)


def onMessage(Connection, Data):
    global _plugin
    _plugin.onMessage(Connection, Data)


def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


def onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile):
    global _plugin
    _plugin.onNotification(Name, Subject, Text, Status, Priority, Sound, ImageFile)


def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)


def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()


# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return


def DumpHTTPResponseToLog(httpResp, level=0):
    if level == 0:
        Domoticz.Debug("HTTP Details (" + str(len(httpResp)) + "):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + "a>'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + "b>'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level + 1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + "c>'" + x + "':'" + str(httpResp[x]) + "'")


def get_val(data_dict, key, ldef=""):
    return str(data_dict.get(key, {}).get("Value", default=ldef))


def UpdateDevice(iUnit, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
    #        if (Devices[Device].DeviceID.strip() == unitname):
    if iUnit in Devices:
        device = Devices[iUnit]
        if device.nValue != nValue or device.sValue != sValue:
            Domoticz.Log(f"Updating device {device.Name} with values {device.nValue}:{device.sValue}")
            device.Update(nValue=nValue, sValue=str(sValue))
