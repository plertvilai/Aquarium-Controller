#!/usr/bin/python

# library for aquarium controller
# revision 02.01
# December, 2018

import io
import os
import time
import picamera
import numpy as np
import RPi.GPIO as GPIO
import datetime as dt
import Adafruit_DHT
#import glob
import bme280
import requests
import ms5837_p3
#------------------------pin assignment------------------------------#
button_pin1 = 27 #for push button
button_pin2 = 16
pump_pin1 = 26
pump_pin2 = 19
float_pin1 = 21
float_pin2 = 20
dht_pin = 6
pwr_ctl_pin = 22 #for controlling 3.3V to peripherals

	
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
		self.waterTemp = 25
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

		#ms5837 setup
		self.bar30 = ms5837_p3.MS5837_02BA()
		self.bar30.setFluidDensity(ms5837_p3.DENSITY_SALTWATER)
		self.bar30.init()
		self.depth = 0

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
		#self.airRH, self.airTemp = Adafruit_DHT.read_retry(self.dht, dht_pin)
		self.floatStat = self.checkFloatSwitch(float_pin1)
		self.floatStat2 = self.checkFloatSwitch(float_pin2)
		self.bar30.read()
		self.waterTemp = self.bar30.temperature(ms5837_p3.UNITS_Centigrade)
		self.depth = self.bar30.depth()*100 #convert to cm
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
		file.write('%.2f,%.2f,%.2f,%.2f,%.2f\n'%(time.time(),self.waterTemp,self.depth,self.bmeData[0],self.bmeData[3]))
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

	def uploadData(self,historic):
		'''Upload data to oceanleaf website.
		Boolean historic: if 1, then write to historical data as well'''
		time.sleep(1)
		payload = {'wtemp':self.waterTemp,'depth':self.depth,'atemp':self.bmeData[0],'humid':self.bmeData[3],'pressure':self.bmeData[1]}
		r = requests.get('http://www.oceanleaf.org/phpScript/writeHomeData.php',params=payload)

		if historic:
			payload = {'wtemp':self.waterTemp,'depth':self.depth,'atemp':self.bmeData[0],'humid':self.bmeData[3],'pressure':self.bmeData[1]}
			r = requests.get('http://www.oceanleaf.org/phpScript/writeHistoricData.php',params=payload)

		return r.text=='OK' #check whether the php script responded.

	def buttonRead(self):
		'''Read push button status.'''
		if GPIO.input(button_pin1):
			self.buttonState = not self.buttonState
			return True
		else:
			return False



