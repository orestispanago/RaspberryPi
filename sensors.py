'''Module containing functions to read RPi sensors'''

from pi_sht1x import SHT1x
import RPi.GPIO as GPIO
import glob
import time
import serial

#creates list with OneWire device pathnames
base_dir = '/sys/bus/w1/devices/'
device_file = glob.glob(base_dir + '28*'+ '/w1_slave')

GPIO.setwarnings(False)
Data_pin = 18
sck_pin = 23
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
''' Sensirion '''
def sensirion():
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
    try:
        # Function contains INFINITE WHILE
        # if sensor disconnected DO NOT CALL function
        # if sensor disconnected, replace while with for i in range(12) SUCCESSFULL
        while True:
            ch1 = _port.read()
            if ch1 == b'\x42':
                ch2 = _port.read()
                if ch2 == b'\x4d':
                    rv += ch1 + ch2
                    rv += _port.read(28)
                    return rv
    except:
        return 'NaN'
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
