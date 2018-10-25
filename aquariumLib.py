#!/usr/bin/python

#library for aquarium controller

import io
import os
import time
import picamera
import numpy as np
import RPi.GPIO as GPIO
import datetime as dt
import Adafruit_DHT
import glob
import bme280

#------------------------pin assignment------------------------------#
button_pin1 = 12 #for push button
button_pin2 = 16
pump_pin1 = 26
pump_pin2 = 19
float_pin1 = 21
float_pin2 = 20
dht_pin = 6
pwr_ctl_pin = 22 #for controlling 3.3V to peripherals

class ds18b20():
	'''Use to read data from DS18B20 temperature sensor'''
	def __init__(self):
		os.system('modprobe w1-gpio')
		os.system('modprobe w1-therm')
		 
		self.base_dir = ''
		self.device_folder = ''
		self.device_file = ''

		self.temp = 0

	def initialization(self):
		self.base_dir = '/sys/bus/w1/devices/'
		self.device_folder = glob.glob(self.base_dir + '28*')[0]
		self.device_file = self.device_folder + '/w1_slave'


	def read_temp_raw(self):
		f = open(self.device_file, 'r')
		lines = f.readlines()
		f.close()
		return lines
 
	def read_temp(self):
	    lines = self.read_temp_raw()
	    while lines[0].strip()[-3:] != 'YES':
	        time.sleep(0.2)
	        lines = self.read_temp_raw()
	    equals_pos = lines[1].find('t=')
	    if equals_pos != -1:
	        temp_string = lines[1][equals_pos+2:]
	        self.temp = float(temp_string) / 1000.0
	        #temp_f = temp_c * 9.0 / 5.0 + 32.0
	        return self.temp
	
class aquariumController():

	def __init__(self):
		#pin mode assignment
		GPIO.setmode(GPIO.BCM)
		GPIO.setup(button_pin1, GPIO.IN)
		GPIO.setup(button_pin2, GPIO.IN)
		GPIO.setup(float_pin1, GPIO.IN)
		GPIO.setup(float_pin2, GPIO.IN)
		GPIO.setup(pump_pin1, GPIO.OUT)
		GPIO.setup(pwr_ctl_pin,GPIO.OUT)
		GPIO.output(pump_pin1, GPIO.LOW)
		GPIO.output(pwr_ctl_pin,GPIO.LOW)

		#GPIO
		self.buttonState = 0 #read button state at the beginning
		self.ledState = 0 #led pin state

		#for environmental data
		self.waterTemp = 0
		self.airTemp = 0
		self.airRH = 0
		self.bmeData = [0,0,0,0] #store bme280 data as [temp,pressure,gauge pressure, rh]

		#for water level trigger
		self.floatSw = 0
		self.floatStat = 0
		self.floatSw2 = 0
		self.floatStat2 = 0
		self.pumpStat = 0 
		self.pumpSafe = 1 #for double safety, if pumpSafe = 0, then pump will stop no matter what

		#for 3.3V peripheral power
		self.pwr = 0

		#for time keeping
		self.time = time.time()
		self.pumpTime = time.time()

		self.dht = Adafruit_DHT.DHT22
		self.ds18 = ds18b20()

		#for error keeping
		self.errCnt = 0

		#RF data
		self.rfData = []

		return


	def powerSwitch(self,state):
		'''Switch the 3.3V power to peripherals. Note that GPIO.LOW = ON'''
		if state: #if the power is on
			self.pwr = 1 #turn it off
			GPIO.output(pwr_ctl_pin,GPIO.LOW)
		else:
			self.pwr = 0 #turn it ON
			GPIO.output(pwr_ctl_pin,GPIO.HIGH)

	def pumpON(self):
		'''Pump water if safety is off.'''
		if self.pumpSafe: #if safety is off
			self.pumpStat = 1
			GPIO.output(pump_pin1, GPIO.HIGH)
			return True
		else: #if statefy triggers, then turn pump off
			GPIO.output(pump_pin1, GPIO.LOW)
			return False

	def pumpOFF(self):
		self.pumpStat = 0
		GPIO.output(pump_pin1, GPIO.LOW)
		return False

	def floatToggle(self,pin,state):
		'''change state of float switch'''
		if pin == 21:
			self.floatSw = state
		else:
			self.floatSw2 = state
		return

	def checkFloatSwitch(self,pin):
		'''Check whether the button is released.
		3 is the default state where button is not pressed.
		1 is when button is kept pressed.
		4 button release
		2 button initial press'''
		if pin == 21:
			prevFloat = self.floatSw
		else:
			prevFloat = self.floatSw2

		curFloat = GPIO.input(pin) #read button

		if curFloat and prevFloat: #if the button is pressed (from being pressed)
			self.floatToggle(pin,1)
			return 1
		elif curFloat and not prevFloat: #if the button is pressed (from not being pressed)
			self.floatToggle(pin,1)
			return 2
		elif not curFloat and not prevFloat: #if the button is not pressed (from not being pressed)
			self.floatToggle(pin,0)
			return 3
		elif not curFloat and prevFloat: #if the button is not pressed (from being pressed)
			self.floatToggle(pin,0)
			return 4
		else:
			return 5

	def pumpSafety(self,trigTime):
		'''set safety trigger time in seconds.'''
		if time.time()-self.pumpTime > trigTime:
			self.pumpSafe = 0
			return True
		else:
			return False

	def updateData(self):
		'''Update environmental data from sensors.'''
		self.waterTemp = self.ds18.read_temp()
		self.airRH, self.airTemp = Adafruit_DHT.read_retry(self.dht, dht_pin)
		self.floatStat = self.checkFloatSwitch(float_pin1)
		self.floatStat2 = self.checkFloatSwitch(float_pin2)
		self.bmeData = bme280.readBME280All()
		return True

	def errCheck(self):
		'''check for errors.'''
		if self.waterTemp < 10:
			self.errCnt  = self.errCnt+1
			return True
		else:
			return False

	def recordData(self,directory):
		'''record data to the directory.
		Data format: unix time, ds18b20, dht22 rh, dht22 temp, bme280 data (4)'''
		file = open(directory+'data.csv','a') 
		file.write('%.2f,%.2f,%.2f,%.2f'%(time.time(),self.waterTemp,self.airRH,self.airTemp))
		for i in range(4):
			file.write('%.2f'%self.bmeData[i])
		file.write('\n')
		file.close()
		return True

	def checkTime(self,delayT):
		'''check whether delayT has passed (in seconds).'''
		if time.time()-self.time > delayT:
			self.time = time.time()
			return True
		else:
			return False

	def getRFdata(self,rfID):
		'''Read RF data from other units.'''
		filename = '/home/pi/aquariumController/rfData/rfID%.2d.csv' %rfID #data[0] is the RF ID

		file = open(filename,'r') #overwrite the existing file 
		data = file.readlines()
		file.close()
		#print(data)
		self.rfData = data[0].split(',')
		return True

	def powerCycle(self,wt):
		'''Perform power cycle of the peripherals.
		wt is the wait time in seconds after rebooting before start taking data.'''
		self.powerSwitch(0) #turn off first
		time.sleep(5) #wait 5 seconds to completely shutdown
		self.powerSwitch(1) #turn back on
		time.sleep(wt)
		return True


