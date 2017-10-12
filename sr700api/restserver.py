#!/usr/bin/env python3
"""
restserver.py

Instantiate a flask restful app and a connection to a BusPirate.
Ideally, this belongs in /bin as a script, but the package works
as currently structured, so leaving it under /busprtspitemp for now.
"""
"""
MIT License

Copyright (c) 2017 int3ll3ct.ly@gmail.com

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from flask import Flask
from flask_restful import Resource, Api, reqparse, request
import logging
from sr700api.version import __version__
import freshroastsr700
from sr700api.max31855kdevice import Max31855kDevice as bp
from sr700api import utils as utils
import logging
logging.basicConfig(filename='sr700_restserver.log',level=logging.WARNING)

app = Flask(__name__)
api = Api(app)

# shut down werkzeug logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.CRITICAL)

# hardware interface
device_bt = bp()  # bean temperature probe
device_sr700 = freshroastsr700.freshroastsr700(ext_sw_heater_drive=True)
# attempt to connect to sr700 device, or connect
# later if not plugged in yet...
device_sr700.auto_connect()


class TestEndpoint(Resource):
    def get(self):
        return {
            'project': 'sr700api',
            'version': __version__
        }


class BeanTemperature(Resource):
    def get(self):
        if device_bt.is_connected():
            probe_t, fault, junc_t, scv, scg, oc = device_bt.read()
            return {
                'bean_temp_c': "%s" % round(probe_t, 1),
                'bean_temp_f': "%s" % round(utils.c_to_f(probe_t), 1),
                'fault': fault,
                'junc_t_c': "%s" % round(junc_t, 1),
                'junc_t_f': "%s" % round(utils.c_to_f(junc_t), 1),
                'fault_scv': scv,
                'fault_scg': scg,
                'fault_oc': oc,
                'error': 'None'
            }
        else:
            return ({

                'bean_temp_c': '0.0',
                'bean_temp_f': '0.0',
                'fault': 1,
                'junc_t_c': '0.0',
                'junc_t_f': '0.0',
                'fault_scv': 0,
                'fault_scg': 0,
                'fault_oc': 0,
                'error': 'Hardware not connected.'
            },
            503
            )


class FanSpeed(Resource):
    """ allows reading & writing of fan speed."""
    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'fan_speed', type=int, choices=range(1, 10),
            required=True,
            help='Fan speed can be 1..9, wheere 1=min, 9=max'
            )

    def get(self):
        if device_sr700.connected:
            return {
                'fan_speed': device_sr700.fan_speed
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )

    def put(self):
        if device_sr700.connected:
            kwargs = self.parser.parse_args()
            fs = kwargs['fan_speed']
            try:
                device_sr700.fan_speed = fs
                return {'fan_speed': fs}
            except freshroastsr700.exceptions.RoasterValueError:
                return (
                    {
                        'error':
                        'Could not set requested value. Out of range?',
                    },
                    400
                    )


class TimeRemaining(Resource):
    """ allows reading & writing of time remaining. This parameter
        doesn't really make sense on a non-ramp/soak method of operation,
        which is what the freshroastsr700 package was designed for.
        This often remains unused."""
    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'time_remaining', type=int, choices=range(1, 600),
            required=True,
            help='Time remaining can be 1..599 seconds.'
            )

    def get(self):
        if device_sr700.connected:
            return {
                'time_remaining': device_sr700.time_remaining
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )

    def put(self):
        if device_sr700.connected:
            kwargs = self.parser.parse_args()
            value = kwargs['time_remaining']
            try:
                device_sr700.time_remaining = value
                return {'time_remaining': value}
            except freshroastsr700.exceptions.RoasterValueError:
                return (
                    {
                        'error':
                        'Could not set requested value. Out of range?',
                    },
                    400
                    )


class TargetTemp(Resource):
    """ When freshroastsr700 is in thermostat mode, this is the set
        point value for the chamber temperature."""
    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'target_temp_c', type=int, choices=range(150, 551),
            help='target_temp can be 150..550 deg F.  Note that '
                 'hardware seems to limit this to 520F.'
            )
        self.parser.add_argument(
            'target_temp_f', type=int, choices=range(150, 551),
            help='target_temp can be 150..550 deg F.  Note that '
                 'hardware seems to limit this to 520F.'
            )

    def get(self):
        if device_sr700.connected:
            # note we're dealing in whole numbers here.
            return {
                'target_temp_f': round(device_sr700.target_temp, 0),
                'target_temp_c': round(
                    utils.f_to_c(device_sr700.target_temp), 0)
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )

    def put(self):
        if device_sr700.connected:
            kwargs = self.parser.parse_args()
            value_c = kwargs['target_temp_c']
            value_f = kwargs['target_temp_f']
            if value_f is None:
                if value_c is not None:
                    value_f = int(round(utils.c_to_f(value_c), 0))
                else:
                    return (
                        {
                            'error':
                            'Must supply target_temp_c or target_temp_f.',
                        },
                        400
                        )
            try:
                device_sr700.target_temp = value_f
                return {
                        'target_temp_f': device_sr700.target_temp,
                        'target_temp_c': int(
                            round(utils.f_to_c(device_sr700.target_temp), 0))
                    }
            except freshroastsr700.exceptions.RoasterValueError:
                return (
                    {
                        'error':
                        'Could not set requested value. Out of range?',
                    },
                    400
                    )


class CurrentTemp(Resource):
    """ This is the sr700's current chamber temperature (below the beans)."""
    def get(self):
        if device_sr700.connected:
            return {
                'current_temp_f': round(device_sr700.current_temp, 1),
                'current_temp_c':
                round(utils.f_to_c(device_sr700.current_temp), 1)
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )


class Dummy(Resource):
    """ Returns a 0 reading at all times, when hardware connected."""
    def get(self):
        if device_sr700.connected:
            return {
                'dummy': 0
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )


class HeaterLevel(Resource):
    """ allows reading & writing of heater level. In this implementation,
        the number of heater segments is left to its default of 8,
        whichc means the acceptable range is 0 to 8 inclusive."""
    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'heater_level', type=int, choices=range(0, 9),
            required=True,
            help='Heater Level can be 0..8, wheere 0=off, 8=max'
            )

    def get(self):
        if device_sr700.connected:
            return {
                'heater_level': device_sr700.heater_level
            }
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )

    def put(self):
        if device_sr700.connected:
            kwargs = self.parser.parse_args()
            value = kwargs['heater_level']
            try:
                device_sr700.heater_level = value
                return {'heater_level': value}
            except freshroastsr700.exceptions.RoasterValueError:
                return (
                    {
                        'error':
                        'Could not set requested value. Out of range?',
                    },
                    400
                    )


class State(Resource):
    """
    allows reading/writing of SR700 state. States can be set, but have
    no effect unless the hardware is detected and time_remaining is
    greater than zero. When time_remaining counts down to 0, the software
    automatically changes the state to idle."""

    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'state', type=str,
            required=True,
            choices=(
                'idle',
                'roasting',
                'cooling',
                'sleeping'
                ),
            help='Current state ' +
                 'of freshroastsr700 module as a string. Possible values: ' +
                 'idle, roasting, cooling, sleeping.'
            )

    def get(self):
        if device_sr700.connected:
            return {'state': device_sr700.get_roaster_state()}
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )

    def put(self):
        if device_sr700.connected:
            args = self.parser.parse_args()
            state = args['state']
            if state == 'idle':
                device_sr700.idle()
            elif state == 'roasting':
                device_sr700.roast()
            elif state == 'cooling':
                device_sr700.cool()
            elif state == 'sleeping':
                device_sr700.sleep()
            else:
                # no way to set other states
                return(
                    {
                        'message':
                        {
                            'state':
                            'No means to set state to ' + state + '.'
                        }
                    },
                    400
                    )
            # success
            return {'state': state}
        else:
            return ({
                'error': 'Hardware not connected.'
            },
            503
            )


class ServerShutdown(Resource):
    """ allows a client to shut down the server.
        In a local server setting, it may be desirable to run the REST API
        server only for an end-user app's lifetime. """

    def __init__(self, *args, **kwargs):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument(
            'server_shutdown', type=str, required=True,
            help='Used to shutdown a local REST API server instance. ' +
                 'Must supply valid server shutdown code.'
            )

    def shutdown_server(self):
        """shuts down the werkzeug server invoked by app.run().
           TODO - change shutdown technique if we change the server type
           from the current non-prod simple one to CherryPy."""
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            logging.error(
                'ServerShutdown.shutdown_server: '
                'Server is not a werkzeug server, cannot shut down.')
            raise RuntimeError(
                'ServerShutdown.shutdown_server: '
                'Server is not a werkzeug server, cannot shut down.')
            return False
        func()
        return True

    def post(self):
        args = self.parser.parse_args(strict=True)
        code = args['server_shutdown']
        if code != 'sr700api':
            return(
                {
                    'message':
                    {
                        'server_shutdown':
                        'Incorrect shutdown code.'
                    }
                },
                400
                )
        # shut down the server
        if self.shutdown_server():
            return {'server_shutdown': 'ok'}
        else:
            return {'server_shutdown': 'fail'}

api.add_resource(TestEndpoint, '/')  # the test endpoint
api.add_resource(BeanTemperature, '/bean_temp')
api.add_resource(Dummy, '/dummy')
api.add_resource(FanSpeed, '/fan_speed')
api.add_resource(TargetTemp, '/target_temp')
api.add_resource(CurrentTemp, '/current_temp')
api.add_resource(State, '/state')
api.add_resource(TimeRemaining, '/time_remaining')
api.add_resource(HeaterLevel, '/heater_level')
api.add_resource(ServerShutdown, '/server_shutdown')

def start_server(debug=False):
    """
    Start the RESTful server and connect to the hardware device.
    Returns:
        True if successful, False otherwise.
    """
    if(device_bt.find_connect()):

        app.run(port=58700, debug=debug)
        # this is a blocking call, will only return once exited
        device_bt.disconnect()
        device_sr700.sleep()
        device_sr700.disconnect()
        return True
    # failed to connect to hardware
    logging.error(
        "restserver.start_server - failed to find temp probe HW, bailing.")
    return False

# this runs when invoked as a script, WE'RE DOING THIS.
if __name__ == '__main__':
    start_server(debug=False)
