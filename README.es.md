[![en](https://img.shields.io/badge/lang-en-red.svg)](https://github.com/ayasystems/froniusHttp/blob/master/README.md)
[![es](https://img.shields.io/badge/lang-es-yellow.svg)](https://github.com/ayasystems/froniusHttp/blob/master/README.es.md)


# FroniusHTTP

ONLY FRONIUS PRIMO WILL BE SUPPORTED, SORRY
SOLO SERÁ SOPORTADO FRONIUS PRIMO

FroniusHTTP domoticz plugin para su integración en domoticz


![Fronius inverter](https://github.com/ayasystems/FroniusHTTP/raw/master/fronius2.jpg)

![Domoticz_Fronius_Plugin](https://github.com/ayasystems/FroniusHTTP/raw/master/froniusDomoticz.jpg)

Más info -> https://domotuto.com/fronius_domoticz_plugin/

## Instalación

1. Clona el repositorio dentro de tu carpeta de plugins de domoticz
```
cd domoticz/plugins
git clone https://github.com/ayasystems/froniusHttp.git
```
2. Reinicia domotiz
```
sudo systemctl stop domoticz
sudo systemctl start domoticz
```
3. Ve a la página de "Hardware" y añade un nuevo hardware, en tipo selecciona "Fronius http"
4. Especifica la ip de tu inversor Fronius
5. Recuerda permitir añadir nuevos dispositivos en el menú de ajustes


## Actualización del plugin


1. Para domoticz 
```
sudo systemctl stop domoticz
```
2. Ve al directorio del plugin y haz un git pull para que actualice la versión 
```
cd domoticz/plugins/froniusHttp
git pull
```
3. Start domoticz
```
sudo systemctl start domoticz
```
 

## También te puede interesar..

Lectura via modbus del inversor fronius

https://github.com/ayasystems/Fronius-node-red-Flow



