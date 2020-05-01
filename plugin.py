# Fronius http python plugin
# @2020
# Author: EA4GKQ
#https://github.com/akleber/fronius-json-tools
"""
<plugin key="FroniusHttp" name="Fronius http" author="EA4GKQ" version="1.0.1" wikilink="https://github.com/ayasystems/froniusHttp" externallink="https://www.fronius.com/es-es/spain/energia-solar/productos">
    <description>
        <h2>Fronius HTTP Pluging</h2><br/>
        <h3>by @ea4gkq</h3>
		<br/>
		<a href="https://domotuto.com/fronius_domoticz_plugin/">https://domotuto.com/fronius_domoticz_plugin/</a>
		<br/>
    </description>
    <params>
        <param field="Address" label="Fronius IP" width="200px" required="true" default="192.168.1.xx"/>
        <param field="Mode1" label="Protocol" width="75px">
            <options>
                <option label="HTTP" value="80"  default="true" />
            </options>
        </param>
        <param field="Mode2" label="Update speed" width="75px">
            <options>
                <option label="Normal" value="Normal"/>
                <option label="High" value="High"  default="true" />
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
except Exception as e:
 errmsg += "Domoticz core start error: "+str(e)
try:
 import json
except Exception as e:
 errmsg += " Json import error: "+str(e)
try:
 import time
except Exception as e:
 errmsg += " time import error: "+str(e)
try:
 import re
except Exception as e:
 errmsg += " re import error: "+str(e)

class FroniusHttp:
    httpConn = None
    interval = 1
    runAgain = interval
    disconnectCount = 0
    sProtocol = "HTTP"
    DAY_ENERGY = ""
    PAC = ""
    TOTAL_ENERGY = ""
    P_PV = ""                  #Producción instantánea
    E_Day = ""                 #Producción del día
    E_Total = ""               #Producción Total
    E_Year = ""                #Producción Año
    P_Grid = ""                #Negativo inyecta Positivo consume   
    P_Load = ""                #Consumo de la red + solar    
    URL1 = "/solar_api/v1/GetMeterRealtimeData.cgi?Scope=System"
    URL1 = "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
    URL2 = "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"
    #192.168.1.51/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData&DeviceId=1 
    current = ""
    def __init__(self):
        return

    def onStart(self):
     Domoticz.Error("onStart: "+errmsg)
     if errmsg =="":
      try:
        Domoticz.Error("onStart - try")	  
        if Parameters["Mode6"] == "": Parameters["Mode6"] = "-1"
        if Parameters["Mode6"] != "0":
            Domoticz.Error("if parameters mode 6: "+Parameters["Mode6"])	  
            Domoticz.Debugging(int(Parameters["Mode6"]))
            Domoticz.Error("DumpConfigToLog")	
            DumpConfigToLog()
        createDevices(self,"FV_POWER")	
        createDevices(self,"TO_GRID")		
        createDevices(self,"FROM_GRID") 	
        createDevices(self,"HOME_LOAD")        
        if (Parameters["Mode1"].strip()  == "443"): self.sProtocol = "HTTPS"
        if (Parameters["Mode2"].strip()  == "High"): Domoticz.Heartbeat(1)
        Domoticz.Error("Address: "+Parameters["Address"])
        Domoticz.Error("port: "+Parameters["Mode1"].strip())
        Domoticz.Error("Address: "+Parameters["Address"].strip())		
        self.httpConn = Domoticz.Connection(Name=self.sProtocol+" Test", Transport="TCP/IP", Protocol=self.sProtocol, Address=Parameters["Address"].strip() , Port=Parameters["Mode1"].strip() )
        self.httpConn.Connect()
      except Exception as e:
        Domoticz.Error("Plugin onStart error: "+str(e))
     else:
        Domoticz.Error("Your Domoticz Python environment is not functional! "+errmsg)

    def onStop(self):
        Domoticz.Log("onStop - Plugin is stopping.")

    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Fronius connected successfully.")
            if(self.current==self.URL2):
               self.current=self.URL1
            else:
               self.current=self.URL2	
            self.current=self.URL1               
            sendData = { 'Verb' : 'GET',
                         'URL'  : self.current,
                         'Headers' : { 'Content-Type': 'text/xml; charset=utf-8', \
                                       'Connection': 'keep-alive', \
                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                       'Host': Parameters["Address"]+":"+Parameters["Mode1"], \
                                       'User-Agent':'Domoticz/1.0' }
                       }
            Connection.Send(sendData)
        else:
            Domoticz.Log("Failed to connect ("+str(Status)+") to: "+Parameters["Address"]+":"+Parameters["Mode1"]+" with error: "+Description)

    def onMessage(self, Connection, Data):
        DumpHTTPResponseToLog(Data)
   
        strData = Data["Data"].decode("utf-8", "ignore")
        Status = int(Data["Status"])
        #LogMessage(strData)

        if (Status == 200):
            if ((self.disconnectCount & 1) == 1):
                #Domoticz.Log("Good Response received from Fronius, Disconnecting.")
                self.httpConn.Disconnect()
            else:
                #Domoticz.Log("Good Response received from Fronius, Dropping connection.")
                self.httpConn = None
            self.disconnectCount = self.disconnectCount + 1
            processResponse(self,Data)     
        elif (Status == 302):
            Domoticz.Log("Fronius returned a Page Moved Error.")
            sendData = { 'Verb' : 'GET',
                         'URL'  : Data["Headers"]["Location"],
                         'Headers' : { 'Content-Type': 'text/xml; charset=utf-8', \
                                       'Connection': 'keep-alive', \
                                       'Accept': 'Content-Type: text/html; charset=UTF-8', \
                                       'Host': Parameters["Address"]+":"+Parameters["Mode1"], \
                                       'User-Agent':'Domoticz/1.0' },
                        }
            Connection.Send(sendData)
        elif (Status == 400):
            Domoticz.Error("Fronius returned a Bad Request Error.")
        elif (Status == 500):
            Domoticz.Error("Fronius returned a Server Error.")
        else:
            Domoticz.Error("Fronius returned a status: "+str(Status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onHeartbeat(self):
        #Domoticz.Trace(True)
        if (self.httpConn != None and (self.httpConn.Connecting() or self.httpConn.Connected())):
            Domoticz.Debug("onHeartbeat called, Connection is alive.")
        else:
            self.runAgain = self.runAgain - 1
            if self.runAgain <= 0:
                if (self.httpConn == None):
                    self.httpConn = Domoticz.Connection(Name=self.sProtocol+" Test", Transport="TCP/IP", Protocol=self.sProtocol, Address=Parameters["Address"], Port=Parameters["Mode1"])
                self.httpConn.Connect()
                self.runAgain = self.interval
        #Domoticz.Trace(False)

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
def LogMessage(Message):
    if Parameters["Mode6"] == "File":
        f = open(Parameters["HomeFolder"]+"http.html","w")
        f.write(Message)
        f.close()
        Domoticz.Log("File written")

def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
def processResponse(self,httpResp):
    #DAY_ENERGY = ""
    #PAC = ""
    #TOTAL_ENERGY = ""
    stringData =  httpResp["Data"].decode("utf-8", "ignore")
    jsonData = json.loads(stringData)
    #Domoticz.Error(stringData)
    if(self.current==self.URL2):
       try:
            self.DAY_ENERGY = str(jsonData['Body']['Data']['DAY_ENERGY']['Values']['1'])
            self.PAC = str(jsonData['Body']['Data']['PAC']['Values']['1'])
            self.TOTAL_ENERGY = str(jsonData['Body']['Data']['TOTAL_ENERGY']['Values']['1'])
            if Parameters["Mode6"] == "-1":        
                Domoticz.Error("DAY_ENERGY: "+self.DAY_ENERGY)
                Domoticz.Error("PAC: "+self.PAC)
                Domoticz.Error("TOTAL_ENERGY: "+self.TOTAL_ENERGY)
       except:
         Domoticz.Debug(str(e))   
    if(self.current==self.URL1):
        try:
            self.P_PV     =  str(jsonData['Body']['Data']['Site']['P_PV'])
            self.E_Day    =  str(jsonData['Body']['Data']['Site']['E_Day'])
            self.E_Total  =  str(jsonData['Body']['Data']['Site']['E_Total'])
            self.E_Year   =  str(jsonData['Body']['Data']['Site']['E_Year'])
            self.P_Grid   =  str(jsonData['Body']['Data']['Site']['P_Grid'])
            self.P_Load   =  str(jsonData['Body']['Data']['Site']['P_Load'] * -1)
            TO_GRID       = jsonData['Body']['Data']['Site']['P_Grid'] * -1
            FROM_GRID     = jsonData['Body']['Data']['Site']['P_Grid'] 
            self.P_PV     =  str(jsonData['Body']['Data']['Site']['P_PV'])
            if Parameters["Mode6"] == "-1": 
                Domoticz.Error("P_PV: "+self.P_PV)
                Domoticz.Error("E_Day: "+self.E_Day)
                Domoticz.Error("E_Total: "+self.E_Total)
                Domoticz.Error("E_Year: "+self.E_Year)
                Domoticz.Error("P_Grid: "+self.P_Grid)## 
                Domoticz.Error("P_Load: "+self.P_Load)## 
            instantaneoFV        = self.P_PV
            acumuladoKwhFV       = self.E_Day#acumulado diario
            if(FROM_GRID>=0):
                UpdateDevice("TO_GRID",      0, "0;0")
                UpdateDevice("FROM_GRID",      0, str(FROM_GRID)+";0")
            
            if(TO_GRID>0):
                UpdateDevice("TO_GRID",      0, str(TO_GRID)+";0")
                UpdateDevice("FROM_GRID",      0, "0;0")
            
            UpdateDevice("FV_POWER",      0, instantaneoFV+";"+acumuladoKwhFV)
            UpdateDevice("HOME_LOAD",      0, self.P_Load+";0")
        except:
         Domoticz.Debug(str(e))   
def DumpHTTPResponseToLog(httpResp, level=0):
    if (level==0): Domoticz.Debug("HTTP Details ("+str(len(httpResp))+"):")
    indentStr = ""
    for x in range(level):
        indentStr += "----"
    if isinstance(httpResp, dict):
        for x in httpResp:
            if not isinstance(httpResp[x], dict) and not isinstance(httpResp[x], list):
                Domoticz.Debug(indentStr + "a>'" + x + "':'" + str(httpResp[x]) + "'")
            else:
                Domoticz.Debug(indentStr + "b>'" + x + "':")
                DumpHTTPResponseToLog(httpResp[x], level+1)
    elif isinstance(httpResp, list):
        for x in httpResp:
            Domoticz.Debug(indentStr + "['" + x + "']")
    else:
        Domoticz.Debug(indentStr + "c>'" + x + "':'" + str(httpResp[x]) + "'")
def createDevices(self,unitname):
      OptionsSensor = {"Custom": "1;Hz"}
      iUnit = -1
      for Device in Devices:
       try:
        if (Devices[Device].DeviceID.strip() == unitname):
         iUnit = Device
         break
       except:
         pass
      if iUnit<0: # if device does not exists in Domoticz, than create it
        try:
         iUnit = 0
         for x in range(1,256):
          if x not in Devices:
           iUnit=x
           break
         Domoticz.Debug("Creating: "+unitname);
         if iUnit==0:
          iUnit=len(Devices)+1	  
         if(unitname=="FROM_GRID"):
          Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
         if(unitname=="TO_GRID"): 
          Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
         if(unitname=="HOME_LOAD"): 
          Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
         if(unitname=="FV_POWER"):
          Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
        except Exception as e:
         Domoticz.Debug(str(e))
         return False
      return 
def UpdateDevice(unitname, nValue, sValue):
    # Make sure that the Domoticz device still exists (they can be deleted) before updating it 
	#        if (Devices[Device].DeviceID.strip() == unitname):
      iUnit = -1
      for Device in Devices:
       try:
        if (Devices[Device].DeviceID.strip() == unitname):
         iUnit = Device
         break
       except:
         pass
      if iUnit>=0: # existe, actualizamos	
            if (Devices[iUnit].nValue != nValue) or (Devices[iUnit].sValue != sValue):
                Devices[iUnit].Update(nValue=nValue, sValue=str(sValue))
                Domoticz.Debug("Update "+str(nValue)+":'"+str(sValue)+"' ("+Devices[iUnit].Name+")")
