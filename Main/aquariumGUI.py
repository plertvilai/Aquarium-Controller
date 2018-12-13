#import ms5837
from gpiozero import Button
from guizero import App, Box, Text, PushButton, Picture
import time
import datetime
import serial
import io
import os
from array import array
from aquariumLib import *
import Adafruit_DHT
import ms5837_p3

display_rows = 2
display_columns = 4
padding = 20
label_size = 18
data_size = 22
laser_was_on = False 

data_types = [
		['BME Gauge','BME Temp','BME RH',''],
		['DS18B20 Temp','DHT22 Temp','DHT22 RH',''],
		['Top Tank','Bot Tank','Err Cnt','']
]

data_prefix = [
		['Recording','Laser On','',''],
		['','','','']
]

data_postfix = [
		['','',' m',' m'],
		[' deg',' deg',' deg',' deg']
]

sensor = ms5837_p3.MS5837_02BA()
sensor.init()
sensor.setFluidDensity(ms5837_p3.DENSITY_SALTWATER)
aqua = aquariumController()

aqua.powerSwitch(1) #turn on peripherals
time.sleep(5)

def get_data():
	# Check inputs

	#errorStat = 0
	
	#update all data
	aqua.updateData()
	# try:
	# 	aqua.updateData()
	# except Exception:
	# 	#errorStat = 1
	# 	pass
	#ms5837 data update
	sensor.read()
	aqua.waterTemp = sensor.temperature(ms5837_p3.UNITS_Centigrade)
	aqua.depth = sensor.depth()

	#aqua.getRFdata(1) #get data from RF #1

	#check system for errors
	if aqua.errCheck(): #if error occurs
		aqua.errCnt = aqua.errCnt+1 #increment error count
		aqua.powerCycle(30) #perform power cycling


	#record data to files
	if(aqua.checkTime(300)): #record data every 5 minutes
		aqua.recordData('/home/pi/aquariumController/')

	# if errorStat:
	# 	errorCnt = errorCnt +1
	# print('Air Temp: %d'%aqua.airTemp)
	# print('Air RH: %d'%aqua.airRH)
	# print('Water Temp: %d'%aqua.waterTemp)
	# print('Float Sw: %d'%aqua.floatSw)

	if aqua.floatStat == 2: #float initial trigger
		aqua.pumpTime = time.time()
		aqua.pumpON()
	elif aqua.floatStat == 1: #kept triggered
		aqua.pumpSafety(10) #check safety stop
		aqua.pumpON()
	elif aqua.floatStat == 4: #trigger released
		aqua.pumpOFF()
		aqua.pumpSafe = 1 #reset pump safety
	else:
		aqua.pumpOFF()



	#------------------GUI Control----------------------------#
	#color define
	colorRed = (255,0,0)
	colorGreen = (0,255,0)
	colorOrange = (255,150,0)
	colorDefault = (225,225,225)
	#sampling box
	# if adv.samplingStat:
	# 	data_boxes[0][1].text='ON'
	# 	data_boxes[0][1].bg = colorGreen
	# else:
	# 	data_boxes[0][1].text='OFF'
	# 	data_boxes[0][1].bg = colorOrange
	# #recording box
	# if adv.recordStat:
	# 	data_boxes[0][0].text='ON'
	# 	data_boxes[0][0].bg = colorGreen
	# else:
	# 	data_boxes[0][0].text='OFF'
	# 	data_boxes[0][0].bg = colorOrange

	#data_boxes[0][3].text='{0:0.2f}'.format(adv.fileNum) 

	# numeric data boxes
	data_boxes[0][0].text='%.2f'  %(aqua.depth*100) + ' cm'
	# data_boxes[0][1].text='%.2f'  %(aqua.bmeData[0]) + ' C'
	# data_boxes[0][2].text='%.2f'  %(aqua.bmeData[3]) + ' %'

	data_boxes[1][0].text='{0:0.2f}'.format(aqua.waterTemp) + ' C'
	data_boxes[1][1].text='{0:0.2f}'.format(aqua.airTemp) + ' C'
	data_boxes[1][2].text='{0:0.2f}'.format(aqua.airRH) + ' %'


	# data_boxes[1][2].text='%d' %errorStat
	data_boxes[2][2].text='%d' %aqua.errCnt
	

	# for refilling 
	# not use in rev01
	#
	# if aqua.pumpStat and aqua.pumpSafe:
	# 	data_boxes[2][1].text='Refilling'
	# 	data_boxes[2][1].bg = colorOrange
	# elif aqua.pumpStat and not aqua.pumpSafe:
	# 	data_boxes[2][1].text='Safety Stop!'
	# 	data_boxes[2][1].bg = colorRed
	# else:
	# 	data_boxes[2][1].text='Water OK'
	# 	data_boxes[2][1].bg = colorGreen
	
	# data_boxes[2][0].text='{0:0.2f}'.format(adv.snr[0]) + ' dB'
	# data_boxes[2][1].text='{0:0.2f}'.format(adv.snr[1]) + ' dB'
	# data_boxes[2][2].text='%d' %aqua.floatStat
	# data_boxes[2][3].text='%d' %aqua.floatStat2
	
	#SNR color display
	#change to orange or red if SNR is low
	if aqua.floatSw==1:
		data_boxes[2][0].text='LOW Water'
		data_boxes[2][0].bg = colorRed
	else:
		data_boxes[2][0].text='Water OK'
		data_boxes[2][0].bg = colorGreen

	if aqua.floatSw2==1:
		data_boxes[2][1].text='LOW Water'
		data_boxes[2][1].bg = colorRed
	else:
		data_boxes[2][1].text='Water OK'
		data_boxes[2][1].bg = colorGreen	
	# for j in range(3):
	# 	if adv.snr[j]<10:
	# 		data_boxes[2][j].bg = colorRed
	# 	elif adv.snr[j]<25:
	# 		data_boxes[2][j].bg = colorOrange
	# 	else:
	# 		data_boxes[2][j].bg = colorDefault


	tkr.value = 'System: ' + str(datetime.datetime.now())

app = App(title="Aquarium GUI", width=800, height=400, layout="grid")

# Build the data display grid
data_boxes = []
for r_idx, row in enumerate(data_types):
	cols  = []
	for c_idx, col in enumerate(row):
		bx = Box(app,grid=[c_idx,r_idx])
		txt_label = Text(bx,text = col)
		txt_label.size = label_size
		pb = PushButton(bx, text = '')
		pb.text_size = data_size
		pb.height=2
		pb.width=8
		pb.bg = (225,225,225)
		# if col == 'Laser On':
		# 	pb.update_command(toggle_laser)
		# if col == 'Recording':
		# 	pb.update_command(toggle_recording)
		cols.append(pb)
	data_boxes.append(cols)

logo = Picture(app, image="/home/pi/aquariumController/logoSmall.gif",grid=[4,0])

# Add a ticker at the bottom of the app
tkr = Text(app,text='System: ',grid=[0,3,4,1])
tkr.size = 18

# start callback and run app
app.repeat(100,get_data)
app.display()

