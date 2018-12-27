'''Reads sensors and uploads to Thingspeak
edit cron job to run every minute'''

from pi_sht1x import SHT1x
import RPi.GPIO as GPIO
import glob
import time
import serial

import http.client, urllib
from socket import gaierror
from datetime import datetime

ChannelID = 'YourThingspeakChannelID'
writeAPIkey = 'YourWriteAPIkey'

#creates list with OneWire device pathnames
base_dir = '/sys/bus/w1/devices/'
device_file = glob.glob(base_dir + '28*'+ '/w1_slave')[0]

GPIO.setwarnings(False)
Data_pin = 3
sck_pin = 5

''' DS '''
def read_temp_raw():
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines
def read_temp():
    try:
        lines = read_temp_raw()
        # TODO consider adding for loop instead of while
        while lines[0].strip()[-3:] != 'YES':
            time.sleep(0.2)
            lines = read_temp_raw()
        equals_pos = lines[1].find('t=')
        if equals_pos != -1:
            temp_string = lines[1][equals_pos+2:]
            temp_c = float(temp_string) / 1000.0
            return temp_c
    except:
        return 'NaN'

def sensirion():
	"""Reads SHT11"""
    with SHT1x(Data_pin, sck_pin, gpio_mode=GPIO.BOARD) as sensor:
        try:
            temp = sensor.read_temperature()
            # if temp fails, humidity fails so second exception is redundant
            humidity = sensor.read_humidity(temp)
        except:
            temp,humidity = 'NaN','NaN'
            #dew_pt = sensor.calculate_dew_point(temp, humidity)
    return [temp,humidity]

'''PM sensor global variables'''
port = serial.Serial('/dev/serial0', baudrate=9600, timeout=2.0)
evenbytes = list(range(4, 28, 2))
oddbytes = list(range(5, 28, 2))

'''PM'''
def read_pm_line(_port):
    rv = b''
    while True:
        ch1 = _port.read()
        if ch1 == b'\x42':
            ch2 = _port.read()
            if ch2 == b'\x4d':
                rv += ch1 + ch2
                rv += _port.read(28)
                return rv
def read_pm():
    pmlist = []
    rcv = read_pm_line(port)
    for x, y in zip(evenbytes, oddbytes):
        try:
            value = rcv[x] * 256 + rcv[y]
            pmlist.append(value)
        except:
            pmlist.append('NaN')
    return pmlist

def uploader(temp1,temp2,rh,pm1,pm2_5,pm10):
	'''Uploads to Thingspeak channel'''
    while True:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(now,temp1,temp2,rh,pm1,pm2_5,pm10,sep=',',end='\n')
        params = urllib.parse.urlencode({'field1': temp1,
                                         'field2': temp2,
                                         'field3': rh,
                                         'field4': pm1,
                                         'field5': pm2_5,
                                         'field6': pm10,
                                         'key': writeAPIkey})
        headers = {"Content-types": "application/x-www-form-urlencoded",
                   "Accept": "text/plain"}
        conn = http.client.HTTPConnection("api.thingspeak.com:80")
        try:
            conn.request("POST", "/update", params, headers)
            response = conn.getresponse()
            if response.status != 200:
                print(now,response.status, response.reason)
                continue
            data = response.read() # Don't know why it is here
            # if data.decode() == '0':
                # print(now, 'Reached 15s channel update limit, value not uploaded')
                # continue
            conn.close()
        except gaierror:
            # Got the same error when: DSL unplugged, WiFi disabled, router off
            print(now, 'No internet connection, value not uploaded')
        break
# TODO: upload PM values
tempDS = read_temp()
tempSH = sensirion()[0]
rh = sensirion()[1]
pm1 =  read_pm()[3]
pm2_5 = read_pm()[4]
pm10 = read_pm()[5]

uploader(tempDS,tempSH,rh,pm1,pm2_5,pm10)
