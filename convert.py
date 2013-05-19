import json
import urllib2

import cherrypy, cherrypy.wsgiserver

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
                adc = _convert_to_mv(data, 
                            intercept = node_settings["intercept"],
                            slope = node_settings["slope"]
                        )

                if settings.DEBUG:
                    print adc

                # convert the appropriate ones to temp values in degC
                #temps = [_convert_to_celcius(adc[pin]) for pin in node_settings["sensor_pins"]]
                for pin in node_settings['sensor_pins']:
                    temp = _convert_to_celcius(adc[pin["pin_id"]])
                    sense.add_event(pin["feed_id"], temp)

                    if settings.DEBUG:
                        print temp

                response_code = sense.publish_events()

                if settings.DEBUG:
                    print "Published events to sen.se - response: %s" % response_code

                cherrypy.response.status = 200
                cherrypy.response.body = ['Data logged']
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
        self.data.append({
            'feed_id': feed_id,
            'value': '%0.2f' % value,
            })

    def publish_events(self):
        """
        Sends all of the events to the sen.se server and responds with a
        status code only
        """

        request = urllib2.Request(self.baseurl)
        request.add_header("sense_key", self.api_key)
        request.add_header("content-type", "application/json")
        request.add_data(json.dumps(self.data).encode('utf-8'))

        try:
            response = urllib2.urlopen(request)
        except HTTPError:
            response.code = 500
        finally:
            self.data = []

        return response.code



def _convert_to_mv(data = "", intercept=0, slope=1):
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

    # apply the calibration regression and drop the first value
    # as this is just buffer from the rn-xv and not a reading
    adc = [(adc-intercept)/slope for adc in mv][1:]

    # now what you have is the state of all the raw sensor values
    return adc

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
