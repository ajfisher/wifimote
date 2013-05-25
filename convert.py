from datetime import datetime
import json
from urllib2 import HTTPError, Request, urlopen 

import cherrypy, cherrypy.wsgiserver
import pytz

import settings
from utils import read_request_line, read_headers

"""
Sets up a server receptacle for the wifly to send data to and then
converts those values to temperature readings and pushes them to 
cosm (now xively) for storage though they could be written anywhere.
"""

# this is super dirty but not much we can do. The RN-XV sends bad headers to
# the webserver, terminating a request with \n\n instead of \r\n as it should
# as such we need to override the cherry py function that deals with this
# so it doesn't error.

cherrypy.wsgiserver.wsgiserver2.HTTPRequest.read_request_line = read_request_line
cherrypy.wsgiserver.wsgiserver2.read_headers = read_headers

class SensorServer:
    """
    Defines a sensor server and the various handlers associated with it.
    """

    @cherrypy.expose
    @cherrypy.tools.caching(on=False)
    def reading(self, **kwargs):
        """
        Exposes a reading that the wifly can trigger by making a GET request.
        Really this should be a post but the device is a bit weak so it comes
        in as a simple get request with the data etc in the query string
        """

        if kwargs.has_key("data") and kwargs.has_key("id"):

            data = kwargs["data"]
            wiflynode = kwargs["id"]

            # now we look up the node ID and make sure there's a setting for it
            if settings.SENSORS.has_key(wiflynode):
                
                node_settings = settings.SENSORS[wiflynode]

                # get the raw values off the node
                adc = _convert_to_mv(data)

                if settings.DEBUG:
                    print adc

                # convert the appropriate ones to temp values in degC
                #temps = [_convert_to_celcius(adc[pin]) for pin in node_settings["sensor_pins"]]
                for pin in node_settings['sensor_pins']:
                    mv = _normalise_adc(adc[pin["pin_id"]], pin["intercept"], pin["slope"])
                    temp = _convert_to_celcius(mv)
                    sense.add_event(pin["feed_id"], temp)

                    if settings.DEBUG:
                        print "ID: %s raw: %s norm: %s temp: %s" % (
                                pin["pin_id"], adc[pin["pin_id"]], mv, temp )

                response_code = sense.publish_events()

                if response_code == 200:
                    # all okay
                    if settings.DEBUG:
                        print "Published events to sen.se - response: %s" % response_code

                    cherrypy.response.status = 200
                    cherrypy.response.body = ['Data logged']
                else:
                    cherrypy.response.status = response_code
                    cherrypy.response.body = ['There was an error of some sort']
            else:

                cherrypy.response.status = 403
                cherrypy.response.body = ['This node not valid']
        else:

            cherrypy.response.status = 404
            cherrypy.response.body = ['Data and ID not present']

        cherrypy.response.headers['Content-type'] = 'text/plain'
        return (cherrypy.response.body)

class Sense:
    """
    Wraps all the bits about posting to open.sen.se 
    """
    baseurl = 'http://api.sen.se/events/'
    data = []
    
    def __init__(self, api_key):
        self.api_key = api_key

    def add_event(self, feed_id, value):
        """
        Adds an event to the payload in order to be sent
        """
        #get the current time
        t = datetime.now(pytz.timezone("Australia/Melbourne")) 
        # the wacky formatting below here is because python likes microseconds
        # but Sen.se only like milliseconds and it expects a particular
        # time zone format with a : in it so there's a bit of manipulation reqd
        tt = (t.strftime("%Y-%m-%dT%H:%M:%S.") +  
                ("%03d" % (t.microsecond/1000)) + t.strftime("%z") )
        tt = tt[:-2] + ":" + tt[-2:]

        self.data.append({
            'feed_id': feed_id,
            'value': '%0.2f' % value,
            'timetag': tt
            })

    def publish_events(self):
        """
        Sends all of the events to the sen.se server and responds with a
        status code only
        """

        request = Request(self.baseurl)
        request.add_header("sense_key", self.api_key)
        request.add_header("content-type", "application/json")
        request.add_data(json.dumps(self.data))

        if settings.DEBUG:
            print request.data

        try:
            response = urlopen(request)
            if settings.DEBUG:
                print response.read()
        except HTTPError, e:
            print "Some sort of HTTP style error occurred: Code: %s, reason: %s" % ( 
                e.code, e.reason)
            print "Package was: %s" % json.dumps(self.data)

        finally:
            self.data = []

        return response.code if "response" in vars() else e.code


def _convert_to_mv(data = ""):
    """
    Takes a hex string from the stream and converts it to a list of mV values
    Also takes the regression values for calibration and deals with them
    """
    n = 4 # number of chars to split by (from RN-XV data sheet

    # split up the values
    datavals = [data[i:i+n] for i in range(0, len(data), n)]

    # pad them with a 0 on the end (as this is removed to make then 2 byte vals)
    shiftedvals = [val + "0" for val in datavals]

    # convert to decimal microvolt vals
    decvals = [int(val, 16) for val in shiftedvals]

    # switch to millivolts
    mv = [val/1000 for val in decvals]

    #get rid of the rubbish buffer vals.
    adc = mv[1:]

    # now what you have is the state of all the raw sensor values
    return adc

def _normalise_adc(mv, intercept=0, slope=1):
    """
    Takes a raw voltage value in mV for the RN-XV pin reading and then converts
    it using the linear regression values to convert it from the ADC. Make sure
    you have done a regression on each pin as they are all different.
    """

    # apply the calibration regression and you have a calibrated value
    return (mv-intercept)/slope

def _convert_to_celcius(mv):
    """
    Takes a mV value and converts it to celcius nominally based on a 
    10mV / degree Kelvin value
    """
    return mv / 10 - 273.15

# set up the sense option.

sense = Sense(settings.SENSE_API_KEY)

# do config on cherrypy and then run it up
cherrypy.config.update({
    'server.socket_host': settings.HOST,
    'server.socket_port': settings.PORT,
})

cherrypy.quickstart(SensorServer())

