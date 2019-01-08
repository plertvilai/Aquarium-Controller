# Distributed with a free-will license.
# Use it any way you want, profit or free, provided it fits in the licenses of its associated works.
# MCP9808
# This code is designed to work with the MCP9808_I2CS I2C Mini Module available from ControlEverything.com.
# https://www.controleverything.com/content/Temperature?sku=MCP9808_I2CS#tabs-0-product_tabset-2

import smbus
import time


class mcp9808():

	def __init__(self,address=0x18):
		'''Initialize an MCP9808 device with the specified address.'''
		self.addr = address 
		self.temp = 0
		# Get I2C bus
		self.bus = smbus.SMBus(1)


	def begin(self):
		'''Call this function to initlialize the device for usage.'''

		# MCP9808 address, 0x18(24)
		# Select configuration register, 0x01(1)
		#		0x0000(00)	Continuous conversion mode, Power-up default
		config = [0x00, 0x00]
		self.bus.write_i2c_block_data(self.addr, 0x01, config)
		# MCP9808 address, 0x18(24)
		# Select resolution rgister, 0x08(8)
		#		0x03(03)	Resolution = +0.0625 / C
		self.bus.write_byte_data(self.addr, 0x08, 0x03)
		return True

	def readTemp(self):
		'''Read temperature in C.'''
		# MCP9808 address, 0x18(24)
		# Read data back from 0x05(5), 2 bytes
		# Temp MSB, TEMP LSB
		data = self.bus.read_i2c_block_data(self.addr, 0x05, 2)

		# Convert the data to 13-bits
		ctemp = ((data[0] & 0x1F) * 256) + data[1]
		if ctemp > 4095 :
			ctemp -= 8192
		ctemp = ctemp * 0.0625
		self.temp = ctemp
		#ftemp = ctemp * 1.8 + 32

		# Output data to screen
		# print "Temperature in Celsius is    : %.2f C" %ctemp
		# print "Temperature in Fahrenheit is : %.2f F" %ftemp
		return ctemp