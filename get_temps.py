#!/usr/bin/python
from w1thermsensor import W1ThermSensor

for sensor in W1ThermSensor.get_available_sensors():
    print("%s - %.2f" % (sensor.id, sensor.get_temperature(W1ThermSensor.DEGREES_F)))
