# WIFIMOTE Simple Temperature Sensor

## Introduction

This code basically provides an endpoint for the RN-XV WiFly device to be able
to send data, where it can be processed and then stored or pushed to other
systems.

## Circuit design

A Fritzing schematic / file is included in the schematics directory. A breadboard
view hasn't been created yet but the schematic is pretty simple. All the gerber
files are also included in the schematics directory which you can use to create
your own boards though note that the holes are set to the size of the box I
use from Jaycar.

Please note that this board is currently untested as I'm waiting for them to
arrive from Fusion PCB.

### RN-XV Overview

The RN-XV WiFly device is very capable though extremely basic. It looks like
an XBee but has a full WiFi stack. It is great for basic use cases where you 
want some sensor monitoring but don't want to worry about ZigBee bridges. The 
device has numerous IO lines and has 4 analog sensor pins, meaning that it can 
be used to monitor a set of analog devices and report their data back.

One aspect of the device is that as it runs a fully compliant WiFi stack it can
talk to any device on the network using standard TCP or UDP connections. It even
ships with firmware options to do basic connections to FTP and HTTP making it
very simple to be able to connect to various services.

In addition, it has the ability to sleep for periods of time then wake up,
associate with the WiFi network, connect to a service, post sensor data and then
go back to sleep, all in a matter of seconds. This makes them very efficient and
can run on a coin battery for reasonable periods of time.

#### Limitations

There are some limitations of the RN-XV device. Notably that the sensors
require calibration as they are not very consistent out of the factory and they
also require some configuration. This document outlines both of these processes.

### Web Request Overview

The WiFly device can post data to a web server using HTTP GET requests with 
parameters passed along the query string. A query string would look like:

    data=051208E408DB669A0A140712080F645E06DB&id=HESTIA&mac=00:06:66:71:3a:d2&bss=00:23:54:27:b1:fb&rtc=567e9&bat=2461&io=510&wake=2&seq=1&cnt=49f&rssi=b3

Where:

* data is the volues from the sensors
* id is the device ID
* mac is the mac address of the device
* rssi is the signal strength
* and all the other data can be looked up in the datasheet as it's not as useful

The data from the sensors is encoded in HEX, as microvolts, using 2 bytes to do 
so (4 hex characters). Unfortauntely the RN- XV actually stores the values as 
5 nibbles but the least significant character is dropped. This means all data 
coming off the web request needs to have a zero padded to the right. Thus:

    AF43

would become:

    AF430

### Web Server Overview

The web server for this application takes incoming messages from the RN-XV,
does the relevant conversion to get their true values and then can either
store them locally or pass them on to a 3rd party aggregator. At the moment
the following data storage systems are supported:

* Open SenSe (open.sen.se)

The web server is a python server using CherryPy as it is lightweight, well
documented and has few dependencies. This can be run on something like a 
Raspberry Pi or other very lightweight device as a server quite easily and a
serious web server environment is not required.

#### Patches to CherryPy

It should be noted that the CherryPy web server has been monkey-patched in two
locations. This is because the RN-XV doesn't send the correct headers as part
of the request. This strict header view that CherryPy has is relaxed with the
monkeypatch to include the way the RN-XV sends its headers (as there's no way
to change this on an embedded system).

## Installation

Download or clone the repository at: github.com/ajfisher/wifimote

It is recommended that virtualenv is used. So create a new virtual environment
for python.

Then complete:

    cd /path/to/repo
    pip install -r requirements.txt

This will download, build and install any python packages required.

To run the web server simply copy the settings.py.template and enter your own
setting and save it as settings.py then run the server as:

    python convert.py

You can run this as a daemon with a variety of means outside the scope of this
document. 

## Setting up the RN-XV

The RN-XV is a simple device that can be accessed over serial (using screen) or
connected via telnet. Read the user manual for much more in depth information.
It is recommended to update the device to the latest firmware before any other
tasks.

Basic configuration requires the following tasks:

* Automatic association to the network
* Getting an IP address
* Setting configuration about what the URL is to request
* Setting the host and port to access
* Setting the sensor map
* Setting the request type (HTTP and data to send)

A basic set of instructions to do the above would look like the following. Note
that the comments after # should NOT be entered

Basic config:

    set option deviceid <name>  # sets the name of the device
    set wlan ssid <SSID>        # use the name of your network
    set wlan pass <pass>        # your password
    set wlan join 1             # Auto join at start up
    set wlan auth 4             # WPA2-PSK but others exist

    set time zone 14            # sets to UTC + 10 - you can't go backwards

Saving:

    save                        # save the current config
    reboot                      # reboot and apply it.

Web request config:

    set ip proto 18             # sets to tcp and http
    set ip host <IP>            # The IP where you're running the server
    set ip remote 8081          # change this if you change it in the settings
    set com remote GET$/reading?data= # URL to request
    set option format 31        # send all the data
    set q sensor 0xFF           # send all sensor states


## Calibrating the RN-XV Sensor

The RN-XV sensor isn't consistent from the factory and as such requires
calibration. The simplest way to do this is with a basic set of readings and
a linear regression. 

Take one sensor (eg SENSOR 2 / Pin 20) and introduce a known voltage between
0 and 2V. This is your known state. Query the hex values (you can do this
via the command interface to the device using show q 2 or just get the values
from the web request). Plot the input voltage and read voltage in two columns
and then perform a least squares linear regression on the values (Excel or Google
docs have these functions available). This will give you the values for
Intercept and Slope that you need to supply into the settings file for the device.

Once this is done you should notice the values are much closer together once
the regression is used on the input. 

## Roadmap

This is the current roadmap:

* Document and produce a proper schematic of the circuit to show how it can be used
* Try to include Xively again once their python library is updated
* storage in json to a local store
* use D3 to create a local visualisation.
* Include other end points and have it configurable.



