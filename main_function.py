#! /usr/bin/env python

import os
import random
import time
#Intel MRAA library
import mraa
import alsaaudio
import wave
import random
from creds import *
import requests
import json
import re
import numpy as np
import cv2
import thread
import time


from memcache import Client

# Button 	= 2
# LED 1 	= 3
# LED 2		= 4
#Settings
button = mraa.Gpio(2) #GPIO Pin with button connected
led_record = mraa.Gpio(3) # LED for recording in progress (old 25)
led_status = mraa.Gpio(4) # LED for Alexa status (old 24)
cap = cv2.VideoCapture(0) #openCV camera device

#device = "plughw:1" # Name of your microphone/soundcard in arecord -L
device = "plughw:3,0" # Name of your microphone/soundcard in arecord -L
#Setup

counter = 0
servers = ["127.0.0.1:11211"]
mc = Client(servers, debug=1)
path = os.path.realpath(__file__).rstrip(os.path.basename(__file__))
mGestureTirgger = 0


def internet_on():
    print "Checking Internet Connection"
    try:
        r =requests.get('https://api.amazon.com/auth/o2/token')
	print "Connection OK"
        return True
    except:
	print "Connection Failed"
    	return False

	
def gettoken():
	token = mc.get("access_token")
	refresh = refresh_token
	if token:
		return token
	elif refresh:
		payload = {"client_id" : Client_ID, "client_secret" : Client_Secret, "refresh_token" : refresh, "grant_type" : "refresh_token", }
		url = "https://api.amazon.com/auth/o2/token"
		r = requests.post(url, data = payload)
		resp = json.loads(r.text)
		mc.set("access_token", resp['access_token'], 3570)
		return resp['access_token']
	else:
		return False
		

def alexa():
	led_status.write(1)
	url = 'https://access-alexa-na.amazon.com/v1/avs/speechrecognizer/recognize'
	headers = {'Authorization' : 'Bearer %s' % gettoken()}
	d = {
   		"messageHeader": {
       		"deviceContext": [
           		{
               		"name": "playbackState",
               		"namespace": "AudioPlayer",
               		"payload": {
                   		"streamId": "",
        			   	"offsetInMilliseconds": "0",
                   		"playerActivity": "IDLE"
               		}
           		}
       		]
		},
   		"messageBody": {
       		"profile": "alexa-close-talk",
       		"locale": "en-us",
       		"format": "audio/L16; rate=16000; channels=1"
   		}
	}
	with open(path+'recording.wav') as inf:
		files = [
				('file', ('request', json.dumps(d), 'application/json; charset=UTF-8')),
				('file', ('audio', inf, 'audio/L16; rate=16000; channels=1'))
				]	
		r = requests.post(url, headers=headers, files=files)
		print(r)
	if r.status_code == 200:
		for v in r.headers['content-type'].split(";"):
			if re.match('.*boundary.*', v):
				boundary =  v.split("=")[1]
		data = r.content.split(boundary)
		for d in data:
			if (len(d) >= 1024):
				audio = d.split('\r\n\r\n')[1].rstrip('--')
		with open(path+"response.mp3", 'wb') as f:
			f.write(audio)
		led_record.write(0)
		os.system('mpg123 -q {}1sec.mp3 {}response.mp3'.format(path, path))
		led_status.write(0)
	else:
		led_record.write(0)
		led_status.write(0)
		for x in range(0, 3):
			time.sleep(.2)
			led_record.write(1)
			time.sleep(.2)
			led_record.write(0)
			led_status.write(0)

def start():
	last = mGestureTirgger
	while True:
		val = mGestureTirgger
		if val != last:
			last = val
			if val == 0 and recorded == True:
				print "released!!" 
				rf = open(path+'recording.wav', 'w') 
				rf.write(audio)
				rf.close()
				inp = None
				alexa()
				print "done" 
			elif val == 1:
				print "pressed"
				led_record.write(1)
				inp = alsaaudio.PCM(alsaaudio.PCM_CAPTURE, alsaaudio.PCM_NORMAL, device)
				inp.setchannels(1)
				inp.setrate(16000)
				inp.setformat(alsaaudio.PCM_FORMAT_S16_LE)
				inp.setperiodsize(500)
				audio = ""
				l, data = inp.read()
				if l:
					audio += data
				recorded = True
		elif val == 1:
			if inp is not None: 
				l, data = inp.read()
				if l:
					audio += data

					
def camera_gesture_trigger():
	# Capture frame-by-frame
	ret, frame = cap.read()
	# Our operations on the frame come here
	gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
	blur = cv2.GaussianBlur(gray,(5,5),0)
	ret,thresh1 = cv2.threshold(blur,70,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
		
	contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
	max_area=0
	   
	for i in range(len(contours)):
		cnt=contours[i]
		area = cv2.contourArea(cnt)
		if(area>max_area):
			max_area=area
			ci=i
	cnt=contours[ci]
	hull = cv2.convexHull(cnt)
	moments = cv2.moments(cnt)

	cnt = cv2.approxPolyDP(cnt,0.01*cv2.arcLength(cnt,True),True)
	hull = cv2.convexHull(cnt,returnPoints = False)

	defects = cv2.convexityDefects(cnt,hull)					
	
	if defects is not None:			
		if defects.shape[0] >= 5:
			return 1
			
	return 0
	
def camera_gesture_thread( threadName, delay):
	global mGestureTirgger
	print "start camera thread!!"
	trigger = 0
	counter = 0
	while True:
		trigger = camera_gesture_trigger()
		if trigger == 1:
			counter+=1
		else:
			counter = 0
			mGestureTirgger = 0
			
		if counter > 5:
			mGestureTirgger = 1 
		

if __name__ == "__main__":
	##MRAA output
	led_status.dir(mraa.DIR_OUT)
	led_record.dir(mraa.DIR_OUT)
	led_status.write(0)
	led_record.write(0)
	#MRAA input
	button.dir(mraa.DIR_IN)
	while internet_on() == False:
		print "."
	token = gettoken()
	os.system('mpg123 -q {}1sec.mp3 {}hello.mp3'.format(path, path))
	for x in range(0, 3):
		time.sleep(.1)
		led_status.write(1)
		time.sleep(.1)
		led_status.write(0)
	try:
		thread.start_new_thread( camera_gesture_thread, ("Thread-1", 2, ) )
	except:
		print "Error: unable to start thread"
   
	start()
	#camera_detect()
	
