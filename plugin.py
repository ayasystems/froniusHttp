# Fronius http python plugin
# @2020
# Author: EA4GKQ
#https://github.com/akleber/fronius-json-tools
# 06/05/2020
# - Añadido dummy con valor medio de Grid de las últimas 30 muestras
# - Mejorada reconexión automática
"""
<plugin key="FroniusHttp" name="Fronius http" author="EA4GKQ" version="1.0.2" wikilink="https://github.com/ayasystems/froniusHttp" externallink="https://www.fronius.com/es-es/spain/energia-solar/productos">
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
from random import seed
from random import gauss
from functools import reduce

class FroniusHttp:
    httpConn = None
    interval = 1
    runAgain = interval
    connectedCount = 0
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
    GRID_W = ""	
    listGrid = [] 
    maxGridList = 30
    avgGrid = 0     
    URL1 = "/solar_api/v1/GetMeterRealtimeData.cgi?Scope=System"
    URL1 = "/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
    URL2 = "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"
    #192.168.1.51/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData&DeviceId=1 
    
    #support for Fronius3.0-1 without Battery
    URL4 = "/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceID=1&DataCollection=CommonInverterData"
    PAC = ""
    UAC = ""                #Grid + solar consumption
    FAC = ""
    IAC = ""
    IDC = ""
    UDC = ""
    UAC = ""
    #End-Fronius3
    
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
        
        if (Parameters["Mode3"].strip() == "Fronius3"):
            createDevices(self,"F_PAC")	
            createDevices(self,"F_FAC")
            createDevices(self,"F_IAC")			
            createDevices(self,"F_IDC") 	
            createDevices(self,"F_UAC") 
            createDevices(self,"F_UDC")

        if (Parameters["Mode3"].strip() == "Fronius6"):
            createDevices(self,"FV_POWER")	
            createDevices(self,"TO_GRID")		
            createDevices(self,"FROM_GRID") 	
            createDevices(self,"HOME_LOAD") 
            createDevices(self,"AVGGRID")


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
    def Average(self):
        if(len(self.listGrid)>self.maxGridList):
            self.listGrid.pop(0)
        Domoticz.Debug("List values: "+str(self.listGrid))    
        self.avgGrid = reduce(lambda a,b: a + b, self.listGrid) / len(self.listGrid)
        self.avgGrid = round(self.avgGrid,0)
    def onConnect(self, Connection, Status, Description):
        if (Status == 0):
            Domoticz.Debug("Fronius connected successfully.")
            if(self.current==self.URL2):
               if (Parameters["Mode3"].strip() == "Fronius3"):
                   self.current = self.URL4
                   Domoticz.Debug("onConnect.#self.current: "+self.current)
               if (Parameters["Mode3"].strip() == "Fronius6"):
                   self.current = self.URL1
                   Domoticz.Debug("onConnect.#self.current: "+self.current)
                   
            else:
               if (Parameters["Mode3"].strip() == "Fronius3"):
                   self.current = self.URL4
                   Domoticz.Debug("onConnect.#self.current: "+self.current)
               if (Parameters["Mode3"].strip() == "Fronius6"):
                   self.current = self.URL1
                   Domoticz.Debug("onConnect.#self.current: "+self.current)
                   
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
                Domoticz.Log("Good Response received from Solax, Disconnecting.")
                self.httpConn.Disconnect()
            else:
                Domoticz.Log("Good Response received from Solax, Dropping connection.")
                self.httpConn = None
            self.disconnectCount = self.disconnectCount + 1
            
            try:
                processResponse(self,Data)
                
            except:
                Domoticz.Error("Plugin onMessage error: "+str(e))
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
                        
            try:            
                Connection.Send(sendData)
            except:
                Domoticz.Error("Plugin onMessage.Connection.Send error: ")
                        
        elif (Status == 400):
            Domoticz.Error("Solax returned a Bad Request Error.")
            self.httpConn.Disconnect()
            self.httpConn = None
        elif (Status == 500):
            Domoticz.Error("Solax returned a Server Error.")
            self.httpConn.Disconnect()
            self.httpConn = None
        else:
            Domoticz.Debug("Solax returned a status: "+str(Status))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Debug("onCommand called for Unit " + str(Unit) + ": Parameter '" + str(Command) + "', Level: " + str(Level))

    def onDisconnect(self, Connection):
        Domoticz.Debug("onDisconnect called for connection to: "+Connection.Address+":"+Connection.Port)

    def onHeartbeat(self):
        if(self.connectedCount>10):
            self.connectedCount = 0
            self.httpConn.Disconnect()
            self.httpConn = None    
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
            else:
                Domoticz.Debug("onHeartbeat called, run again in "+str(self.runAgain)+" heartbeats.")
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
    
    #Fronius3
    self.ErrorCode    =  str(jsonData['Body']['Data']['DeviceStatus']['ErrorCode'])
    self.LEDColor     =  str(jsonData['Body']['Data']['DeviceStatus']['LEDColor'])
    Domoticz.Debug("ErrorCode.processResponse: " + str(self.ErrorCode))
    Domoticz.Debug("LEDColor.processResponse: " + str(self.LEDColor))    

    if(int(self.LEDColor) == 2):
        Domoticz.Debug("self.LEDColor.processResponse LED Status is: GREEN : " + str(self.LEDColor)) 
        if (Parameters["Mode3"].strip() == "Fronius3"):
            self.current = self.URL4
            Domoticz.Debug("onConnect.#self.current: "+self.current)
        if (Parameters["Mode3"].strip() == "Fronius6"):
            self.current = self.URL1
            Domoticz.Debug("onConnect.#self.current: "+self.current)
    else:
        if (Parameters["Mode3"].strip() == "Fronius3"):
            self.current = self.URL4
            Domoticz.Debug("onConnect.#self.current: "+self.current)
        if (Parameters["Mode3"].strip() == "Fronius6"):
            self.current = self.URL1
            Domoticz.Debug("onConnect.#self.current: "+self.current)        
    #Fronius3
    
    
    if(self.current==self.URL2):
       try:
            self.DAY_ENERGY = str(jsonData['Body']['Data']['DAY_ENERGY']['Values']['1'])
            self.PAC = str(jsonData['Body']['Data']['PAC']['Values']['1'])
            self.TOTAL_ENERGY = str(jsonData['Body']['Data']['TOTAL_ENERGY']['Values']['1'])
            if Parameters["Mode6"] == "-1":        
                Domoticz.Error("DAY_ENERGY: "+self.DAY_ENERGY)
                Domoticz.Error("PAC: "+self.PAC)
                Domoticz.Error("TOTAL_ENERGY: "+self.TOTAL_ENERGY)
                self.connectedCount = 0
       except:
         Domoticz.Debug(str(e))

    #Fronius3
    if (Parameters["Mode3"].strip() == "Fronius3"):
        
        if((self.current==self.URL1 or self.current==self.URL4) and int(self.LEDColor) == 2 ):
            try:
                self.E_Day    =  str(jsonData['Body']['Data']['DAY_ENERGY']['Value'])
                self.E_Total  =  str(jsonData['Body']['Data']['TOTAL_ENERGY']['Value'])
                self.E_Year   =  str(jsonData['Body']['Data']['YEAR_ENERGY']['Value'])
                try:
                    self.PAC     =  str(jsonData['Body']['Data']['PAC']['Value'])
                    self.UAC      = str(jsonData['Body']['Data']['UAC']['Value'])
                    self.UDC      = str(jsonData['Body']['Data']['UDC']['Value'])
                    self.IAC      = str(jsonData['Body']['Data']['IAC']['Value'])
                    self.IDC      = str(jsonData['Body']['Data']['IDC']['Value'])
                    self.FAC      = str(jsonData['Body']['Data']['FAC']['Value']) 
                    instantaneoFV        = self.PAC
                    acumuladoKwhFV       = self.E_Day#daily accumulated
                except:
                    Domoticz.Error("Plugin json Query(F_XXX, error: "+str(e))
 

                Domoticz.Debug("self.PAC.processResponse.URL4  : " + str(self.PAC))
                Domoticz.Debug("self.E_Day.processResponse.URL4 : " + str(self.E_Day))
                
                if Parameters["Mode6"] == "-1": 
                    Domoticz.Error("F_PAC: "+self.PAC)
                    Domoticz.Error("E_Day: "+self.E_Day)
                    Domoticz.Error("E_Total: "+self.E_Total)
                    Domoticz.Error("E_Year: "+self.E_Year)
                    Domoticz.Error("F_UAC: "+self.UAC)
                    Domoticz.Error("F_UDC: "+self.UDC)                 
                    Domoticz.Error("F_IAC: "+self.IAC)
                    Domoticz.Error("F_IDC: "+self.IDC)                
                    Domoticz.Error("F_FAC: "+self.FAC)

                try:            
                    UpdateDevice("F_PAC",      0, instantaneoFV+";"+acumuladoKwhFV)
                    UpdateDevice("F_UAC",      0, self.UAC+";0")
                    UpdateDevice("F_UDC",      0, self.UDC+";0")
                    UpdateDevice("F_FAC",      0, self.FAC+";0")
                    UpdateDevice("F_IAC",      0, self.IAC+";0")
                    UpdateDevice("F_IDC",      0, self.IDC+";0")
                except:
                    Domoticz.Error("Plugin UpdateDevice(F_XXX, error: "+str(e))
               
                self.connectedCount = 0
            except:
             Domoticz.Error("Plugin processResponse error: "+str(e))   
    
        
    if (Parameters["Mode3"].strip() == "Fronius6"):    
        
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
                self.listGrid.append(FROM_GRID)
                self.Average()       
                if Parameters["Mode6"] == "-1": 
                    Domoticz.Error("P_PV: "+self.P_PV)
                    Domoticz.Error("E_Day: "+self.E_Day)
                    Domoticz.Error("E_Total: "+self.E_Total)
                    Domoticz.Error("E_Year: "+self.E_Year)
                    Domoticz.Error("P_Grid: "+self.P_Grid)## 
                    Domoticz.Error("P_Load: "+self.P_Load)## 
                    Domoticz.Error("List: "+str(self.listGrid))
                    Domoticz.Error("AVG Grid: "+str(round(self.avgGrid,0)))     
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
                UpdateDevice("AVGGRID",       0, self.avgGrid)
                self.connectedCount = 0
            except:
             Domoticz.Debug(str(e))  
    #Fronius3

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
      OptionsSensorAVG = {"Custom": "1;w"}
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
        #Fronius3      
         if (Parameters["Mode3"].strip() == "Fronius3"):
          if(unitname=="F_IDC"): #amper
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=23,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="F_IAC"): #amper
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=23,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="F_FAC"): #custom
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=31,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="F_UAC"): #voltage
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=8,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="F_UDC"): #voltage
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=8,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="F_PAC"):
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
         
         if (Parameters["Mode3"].strip() == "Fronius6"):
          if(unitname=="FROM_GRID"):
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="TO_GRID"): 
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="HOME_LOAD"): 
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="FV_POWER"):
            Domoticz.Device(Name=unitname, Unit=iUnit,Type=243,Subtype=29,Switchtype=0,Used=1,DeviceID=unitname).Create()
          if(unitname=="AVGGRID"):		
            Domoticz.Device(Name=unitname, Unit=iUnit,TypeName='Custom',Options=OptionsSensorAVG,Used=1,DeviceID=unitname).Create()          
          
    #Fronius3      
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
