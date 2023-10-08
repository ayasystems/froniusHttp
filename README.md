[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/ayasystems/froniusHttp/blob/master/README.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/ayasystems/froniusHttp/blob/master/README.es.md)


# FroniusHTTP
FroniusHTTP Domoticz plugin to let you integrate your inverters with your HA.

## Constrains
Only single instance of the inverter is supported.

![Fronius inverter](https://github.com/ayasystems/FroniusHTTP/raw/master/fronius2.jpg)

![Domoticz_Fronius_Plugin](https://github.com/ayasystems/FroniusHTTP/raw/master/froniusDomoticz.jpg)

More information (Spanish language only) -> https://domotuto.com/fronius_domoticz_plugin/

## Installation

1. Navigate to the Domoticz's plugins location
```shell
cd domoticz/plugins
```
2. Clone the repository
```shell
git clone https://github.com/ayasystems/froniusHttp.git
```   
2. Restart Domoticz
```shell
sudo systemctl restart domoticz
```
3. Go to the "Hardware" page and add new hardware, in type select "Fronius http"
4. Configure your devices on the configuration page

NOTE: Remember to allow adding new devices in the settings menu

## Plugin update

1. Navigate to the plugin location 
```shell
cd domoticz/plugins/froniusHttp
```
2. Pull latest plugin version
```shell
git pull
```
3. Restart Domoticz
```
sudo systemctl start domoticz
```
