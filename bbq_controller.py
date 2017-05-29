#!/usr/bin/python

import sys, os, datetime, argparse, ConfigParser, collections
from time import sleep
from w1thermsensor import W1ThermSensor
import RPi.GPIO as GPIO
import plotly.plotly as py
import plotly.tools as tls
import plotly.graph_objs as go

args={}
counter=0
Motor1A = 16
Motor1B = 18
Motor1E = 22
P = 5
I = .1
D = 10
B = 0
c={}
pit_temp = 0
meat_temp = 0
target_temp = 0
current_temp = 0
count = 0
fanSpeed = 0
accumulatedError = 0
sum = 0

def setup_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('-v', '--verbose', dest='verbose', action='store_true')
	parser.add_argument('-q', '--quiet', dest='quiet', action='store_true')
	parser.add_argument('-x', '--demo', dest='demo', action='store_true')
	parser.add_argument('-d', '--docker', dest='docker', action='store_true')
	global args
	args = parser.parse_args()

def log_verbose( string ):
	global args
	if args.verbose:
		print string
	return

def read_config():
	config = ConfigParser.RawConfigParser()
	config.read('bbq_controller.cfg')
	con = collections.namedtuple('config', ['pit', 'meat', 'set_temp', 'alert_min_temp', 'alert_max_temp'])
	global c
	c = con(config.get('Sensors', 'pit_sensorid'), config.get('Sensors', 'meat_sensorid'), config.get('Configuration', 'set_temp'), config.get('Configuration', 'alert_min_temp'), config.get('Configuration', 'alert_max_temp'))

def getos(name):
	return os.getenv(name)

def setup_stream():
	if args.docker:
		tls.set_credentials_file(username=getos('py_user'), api_key=getos('py_api'), stream_ids=[getos('py_1'),getos('py_2'),getos('py_3')])
	log_verbose("Setting up Stream...")
	filename='bbq_streaming'
	title='BBQ Streaming'
	stream_tokens = tls.get_credentials_file()['stream_ids']
	token_1 = stream_tokens[-1]
	log_verbose("Pit Temp Stream Token " + token_1)
	token_2 = stream_tokens[-2]
	log_verbose("Meat Temp Stream Token " + token_2)
	token_3 = stream_tokens[-3]
	log_verbose("Motor Stream Token " + token_3)
	stream_id1 = dict(token=token_1, maxpoints=60)
	stream_id2 = dict(token=token_2, maxpoints=60)
	stream_id3 = dict(token=token_3, maxpoints=60)
	trace1 = go.Scatter(x=[], y=[], stream=stream_id1, name='Pit Temp')
	trace2 = go.Scatter(x=[], y=[], stream=stream_id2, name='Meat Temp')
	trace3 = go.Scatter(x=[], y=[], stream=stream_id3, name='Motor Percent')
	data = [trace1, trace2, trace3]
	layout = dict(title = title,
		xaxis = dict(title = 'Date'),
		yaxis = dict(title = 'Temperature (degrees F)'),
		shapes=[{
			'type': 'line',
			'xref': 'paper',
			'x0': 0,
			'y0': c.set_temp,
			'x1': 1,
			'y1': c.set_temp, # ditto
			'line': {
				'color': 'rgb(185, 52, 52)',
                                'width': 1,
                                'dash': 'dash',
			},
		}]
	)
	fig = go.Figure(data=data, layout=layout)
	plot_url = py.plot(fig, filename=filename)
	global s_1
	s_1 = py.Stream(stream_id=token_1)
	global s_2
	s_2 = py.Stream(stream_id=token_2)
	global s_3
	s_3 = py.Stream(stream_id=token_3)
	s_1.open()
	s_2.open()
	s_3.open()
	log_verbose("Done Setting up Stream\n")

def get_temp( sensor_id ):
	if args.demo:
		global counter
		counter += 1
		return counter
	else:
		sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, sensor_id)
		return sensor.get_temperature(W1ThermSensor.DEGREES_F)

def setup_motor():
	GPIO.setmode(GPIO.BOARD)
	global Motor1A
	global Motor1B
	global Motor1E

	GPIO.setup(Motor1A,GPIO.OUT)
	GPIO.setup(Motor1B,GPIO.OUT)
	GPIO.setup(Motor1E,GPIO.OUT)

	GPIO.output(Motor1B,GPIO.LOW)
	GPIO.output(Motor1E,GPIO.HIGH)

	global p
	p = GPIO.PWM(Motor1A, 50)
	p.start(0)

def loop():
	global P,I,D,B,pit_temp,meat_temp,current_temp,target_temp,count,fanSpeed,accumulatedError,sum,meat_temp
	while True:
		date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
		pit_temp = str(get_temp(c.pit))
		meat_temp = str(get_temp(c.meat))
		print ("Current Pit Temperature: " + pit_temp)
		print ("Current Meat Temperature: " + meat_temp)
		print
		s_1.write(dict(x=date,y=pit_temp))
		s_2.write(dict(x=date,y=meat_temp))
		current_temp = int(get_temp(c.pit))
		target_temp = int(c.set_temp)
		error = (target_temp) - (current_temp)
		log_verbose("Error: " + str(error))
		if 0 < fanSpeed and fanSpeed < 100:
			accumulatedError = accumulatedError + error
			log_verbose("accumulatedError: " + str(accumulatedError))
		sum = sum + current_temp
		count += 1	
		averageTemp = sum / count
		log_verbose("Average Temp: %d" % averageTemp)
		fanSpeed = B + ( P * error ) + ( I * accumulatedError ) + ( D * (averageTemp - current_temp)) 
		if fanSpeed <= 0:
			s_3.write(dict(x=date,y=0))
			p.ChangeDutyCycle(0)
		elif fanSpeed >= 100: 
			s_3.write(dict(x=date,y=100))
			p.ChangeDutyCycle(100)
		else:
			s_3.write(dict(x=date,y=fanSpeed))
			p.ChangeDutyCycle(fanSpeed)
		print "Fan Speed: %d" % fanSpeed
		if args.demo:
			sleep(1)

def main():
	setup_args()
	read_config()
	setup_stream()
	setup_motor()

	print ("Pit Temperature Sensor: " + str(c.pit))
	print ("Meat Temperature Sensor: " + str(c.meat))
	log_verbose("Starting Program...")
	print ("Set Temperature: " + str(c.set_temp))
	print ("Alert Min Temperature: " + str(c.alert_min_temp))
	print ("Alert Max Temperature: " + str(c.alert_max_temp))
	print
	try:
		loop()
	except KeyboardInterrupt:
		print 'interrupted!'
		p.stop()
		GPIO.cleanup()
	except:
		print "Unexpected error:", sys.exc_info()[0]
		p.stop()
		GPIO.cleanup()
		raise
		

if __name__ == "__main__":
	main()
