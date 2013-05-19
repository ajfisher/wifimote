# WIFIMOTE Simple Temperature Sensor

## Introduction

This code basically provides an endpoint for the RN-XV WiFly device to be able
to send data, where it can be processed and then stored or pushed to other
systems.

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

## Installation

Download or clone the repository at: []

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

### Configuring the RN-XV device

### Calibrating the RN-XV Sensor

The RN-XV sensor 
