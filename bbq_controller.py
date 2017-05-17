#!/usr/bin/python

from time import sleep
import argparse
from w1thermsensor import W1ThermSensor
import ConfigParser
import collections
import RPi.GPIO as GPIO

parser = argparse.ArgumentParser()
parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
parser.add_argument('-q', '--quiet', dest='quiet', action='store_true')
args = parser.parse_args()

def read_config():
	config = ConfigParser.RawConfigParser()
	config.read('bbq_controller.cfg')
	con = collections.namedtuple('config', ['pit', 'meat', 'set_temp'])
	c = con(config.get('Sensors', 'pit_sensorid'), config.get('Sensors', 'meat_sensorid'), config.get('Configuration', 'set_temp'))
	return c

def get_temp( sensor_id ):
	sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, sensor_id)
	return sensor.get_temperature(W1ThermSensor.DEGREES_F)

def log_verbose( string ):
	if args.verbose:
		print string
	return

def main():
	GPIO.setmode(GPIO.BOARD)
	Motor1A = 16
	Motor1B = 18
	Motor1E = 22

	GPIO.setup(Motor1A,GPIO.OUT)
	GPIO.setup(Motor1B,GPIO.OUT)
	GPIO.setup(Motor1E,GPIO.OUT)

	GPIO.output(Motor1B,GPIO.LOW)
	GPIO.output(Motor1E,GPIO.HIGH)

	p = GPIO.PWM(Motor1A, 50)
	p.start(0)

	P = 5
	I = .1
	D = 10
	B = 0
	count = 0
	fanSpeed = 0
	accumulatedError = 0
	sum = 0

	config = read_config()
	print ("Pit Temperature Sensor: " + str(config.pit))
	print ("Meat Temperature Sensor: " + str(config.meat))
	log_verbose("Starting Program...")
	print ("Set Temperature: " + str(config.set_temp))
	print
	try:
		while True:
			print ("Current Pit Temperature: " + str(get_temp(config.pit)))
			print ("Current Meat Temperature: " + str(get_temp(config.meat)))
			print
                        current_temp = int(get_temp(config.pit))
			target_temp = int(config.set_temp)
                        error = (target_temp) - (current_temp)
			log_verbose("Error: " + str(error))
			if 0 < fanSpeed and fanSpeed < 100:
				accumulatedError = accumulatedError + error
				log_verbose("accumulatedError: " + str(accumulatedError))
			sum = sum + current_temp
			count = count + 1	
			averageTemp = sum / count
			log_verbose("Average Temp: %d" % averageTemp)
			fanSpeed = B + ( P * error ) + ( I * accumulatedError ) + ( D * (averageTemp - current_temp)) 
			if fanSpeed <= 0:
				p.ChangeDutyCycle(0)
			elif fanSpeed >= 100: 
				p.ChangeDutyCycle(100)
			else:
				p.ChangeDutyCycle(fanSpeed)
			print "Fan Speed: %d" % fanSpeed
	except KeyboardInterrupt:
		print 'interrupted!'
		p.stop()
		GPIO.cleanup()
	except: 
		p.stop()
		GPIO.cleanup()
		

if __name__ == "__main__":
	main()
