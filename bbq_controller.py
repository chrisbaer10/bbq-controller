#!/usr/bin/python

import sys, os, datetime, argparse, ConfigParser, collections, time
from time import sleep
from w1thermsensor import W1ThermSensor
import RPi.GPIO as GPIO
import plotly.plotly as py
import plotly.tools as tls
import plotly.graph_objs as go
from pushover import Client
import plotly.plotly as py
import plotly.graph_objs as go
import pandas as pd
import plotly.exceptions as pe

args={}
counter=0
Motor1A = 16
Motor1B = 18
Motor1E = 15
P = 5
I = .1
D = 10
B = 0
c={}
pit_temp = 0
meat1_temp = 0
meat2_temp = 0
target_temp = 0
current_temp = 0
count = 0
fanSpeed = 0
accumulatedError = 0
sum = 0
tempRangeMet = False
fmt = '%Y-%m-%d %H:%M:%S.%f'
alertLastSent = datetime.datetime.now()
plotLastSent = datetime.datetime.now()
timestr = time.strftime("%Y%m%d-%H%M%S")
plotted = False

def send_push(message, title):
	Client().send_message(message, title=title)
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
	con = collections.namedtuple('config', ['pit', 'meat1', 'meat2', 'set_temp', 'alert_min_temp', 'alert_max_temp', 'alert_max_interval_sec', 'plot_max_interval_sec'])
	global c
	c = con(config.get('Sensors', 'pit_sensorid'), config.get('Sensors', 'meat1_sensorid'), config.get('Sensors', 'meat2_sensorid'), config.get('Configuration', 'set_temp'), config.get('Configuration', 'alert_min_temp'), config.get('Configuration', 'alert_max_temp'), config.get('Configuration', 'alert_max_interval_sec'), config.get('Configuration', 'plot_max_interval_sec'))

def getos(name):
	return os.getenv(name)

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

def create_plot():
	global timestr,plotLastSent,plotted,now
	print "Creating plot from " + timestr + ".csv"
	# TODO replace pandas with something else... takes a long time to download 
	df = pd.read_csv(timestr+'.csv')
	trace1 = go.Scattergl(x = df['date'], y = df['pit_temp'], name='Pit Temp (F)')
	trace2 = go.Scattergl(x = df['date'], y = df['meat1_temp'], name='Meat Temp (F)')
	trace3 = go.Scattergl(x = df['date'], y = df['meat2_temp'], name='Meat Temp (F)')
	trace4 = go.Scattergl(x = df['date'], y = df['fanSpeed'], name='Fan Speed %')
	layout = go.Layout(title='Baer BBQ - ' + timestr, plot_bgcolor='rgb(230, 230,230)', showlegend=True)
	fig = go.Figure(data=[trace1,trace2,trace3,trace4], layout=layout)
	try:
		url = py.plot(fig, filename='Baer BBQ - ' + timestr)
		send_push("Plotly URL: " + url, "Started Plotly")
		plotLastSent = now
		plotted = True
	except pe.PlotlyRequestError as detail:
		print "Unable to create plot...", detail

def loop():
	global P,I,D,B,pit_temp,meat1_temp,meat2_temp,current_temp,target_temp,count,fanSpeed,accumulatedError,sum,tempRangeMet,alertLastSent,f,timestr,plotLastSent,plotted,now
	f = open(timestr+'.csv', 'w')
	f.write('date' + ',' + 'pit_temp' + ',' + 'meat1_temp' + ',' + 'meat2_temp' + ',' + 'fanSpeed' + '\n')
	f.close()
	with open(timestr+'.csv', 'a') as csv_file:
		while True:
			now = datetime.datetime.now()
			date = now.strftime(fmt)
			pit_temp = str(get_temp(c.pit))
			meat1_temp = str(get_temp(c.meat1))
			meat2_temp = str(get_temp(c.meat2))
			print ("Current Pit Temperature: " + pit_temp)
			print ("Current Meat1 Temperature: " + meat1_temp)
			print ("Current Meat2 Temperature: " + meat2_temp)
			print
			current_temp = int(get_temp(c.pit))
			print "Alert Last Sent : " + alertLastSent.strftime(fmt)
			print "Plot Last Sent : " + plotLastSent.strftime(fmt)
			if int(current_temp) > int(c.alert_min_temp) and int(current_temp) < int(c.alert_max_temp):
				# set alerting to true now
				tempRangeMet = True
			alert_diff_sec = (now-alertLastSent).total_seconds()
			if int(current_temp) < int(c.alert_min_temp) and tempRangeMet and int(alert_diff_sec) > int(c.alert_max_interval_sec):
				print "Temperature is too low... sending an alert!"
				send_push("Temperature is too low... " + str(current_temp) + " at " + date, "BBQ - Low - " + str(current_temp))
				alertLastSent = now
			if int(current_temp) > int(c.alert_max_temp) and tempRangeMet and int(alert_diff_sec) > int(c.alert_max_interval_sec): 
				print "Temperature is too hot... sending an alert!"
				send_push("Temperature is too HOT... " + str(current_temp) + " at " + date, "BBQ - HOT - " + str(current_temp))
				alertLastSent = now
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
				plotFanSpeed = 0
				p.ChangeDutyCycle(0)
			elif fanSpeed >= 100: 
				plotFanSpeed = 100
				p.ChangeDutyCycle(100)
			else:
				plotFanSpeed = fanSpeed
				p.ChangeDutyCycle(fanSpeed)
			print "Fan Speed: %d" % fanSpeed
			csv_file.write(date + ',' + pit_temp + ',' + meat1_temp + ',' + meat2_temp + ',' + str(plotFanSpeed) + '\n')
			csv_file.flush()
			plot_diff_sec = (now-plotLastSent).total_seconds()
			if int(plot_diff_sec) > int(c.plot_max_interval_sec) or not plotted:
				create_plot()
			if args.demo:
				sleep(1)
def main():
	setup_args()
	read_config()
	setup_motor()
	
	print ("Pit Temperature Sensor: " + str(c.pit))
	print ("Meat1 Temperature Sensor: " + str(c.meat1))
	print ("Meat2 Temperature Sensor: " + str(c.meat2))
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
