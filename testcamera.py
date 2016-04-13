import numpy as np
#include openCV
import cv2
#Intel MRAA library
import mraa

button = mraa.Gpio(2) #GPIO Pin with button connected
cap = cv2.VideoCapture(0)

last =0
while(True):
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

	#for i in range(defects.shape[0]):

	if defects is not None:
		print((defects.shape[0]))

#check button to exit the loop
	last = button.read()
	if last ==1:
		break
	# When everything done, release the capture

cap.release()
cv2.destroyAllWindows()




