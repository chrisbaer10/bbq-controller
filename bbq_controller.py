#!/usr/bin/python

import argparse
from w1thermsensor import W1ThermSensor
import ConfigParser
import collections

parser = argparse.ArgumentParser()
parser.add_argument('settemp', type=int, help='temperature to maintain')
parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
parser.add_argument('-q', '--quiet', dest='quiet', action='store_true')
args = parser.parse_args()

def read_config():
	config = ConfigParser.RawConfigParser()
	config.read('bbq_controller.cfg')
	con = collections.namedtuple('config', ['pit', 'meat'])
	c = con(config.get('Sensors', 'pit_sensorid'), config.get('Sensors', 'meat_sensorid'))
	return c

def get_temp( sensor_id ):
	sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, sensor_id)
	return sensor.get_temperature(W1ThermSensor.DEGREES_F)

def log_verbose( string ):
	if args.verbose:
		print string
	return

def main():
	log_verbose("Reading Config File...")
	config = read_config()
	print ("Pit Temperature Sensor: " + str(config.pit))
	print ("Meat Temperature Sensor: " + str(config.meat))
	log_verbose("Starting Program...")
	print ("Set Temperature: " + str(args.settemp))
	print ("Current Pit Temperature: " + str(get_temp(config.pit)))
if __name__ == "__main__":
    main()
