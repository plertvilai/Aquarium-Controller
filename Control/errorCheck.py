#!/usr/bin/env python

import subprocess
import requests
import time

while(1):

	time.sleep(300) #wait 5 minutes before next checking
	
	r = requests.get('http://www.oceanleaf.org/phpScript/checkStatus.php')
	print r.text
	time.sleep(5)

	if r.text=='0': #error occurs
		r2 = requests.get('http://www.oceanleaf.org/phpScript/piError.php')
		subprocess.call("sudo reboot",shell=True)  #reboot 

	