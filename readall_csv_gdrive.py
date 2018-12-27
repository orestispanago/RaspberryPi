""" Reads DS18B20, SHT11 and PMS5003 
Writes to .csv
Uploads to GoogleDrive
"""

import serial
from datetime import datetime, timezone
import csv
import os
import glob
from pi_sht1x import SHT1x
import RPi.GPIO as GPIO
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from apscheduler.schedulers.blocking import BlockingScheduler

launch_datetime = '2018-02-09 20:42:00'

'''DS temp sensor global variables'''
base_dir = '/sys/bus/w1/devices/'
#creates list with device paths
device_files = glob.glob(base_dir + '28*'+ '/w1_slave')

'''SHT humidity + temp sensor global variables'''
# GPIO.setwarnings(False)
Data = [18,16]
sck = [23,21]

'''PM sensor global variables'''
port = serial.Serial('/dev/serial0', baudrate=9600, timeout=2.0)
bytes2read = 28
evenbytes = list(range(4, bytes2read, 2))
oddbytes = list(range(5, bytes2read, 2))

headers = ['Datetime UTC', 'TempDS1', 'TempDS2', 'TempSH1', 'HumSH1', 'TempSH2',
'HumSH2','PM1.0(CF=1)', 'PM2.5(CF=1)', 'PM10 (CF=1)',
'PM1.0 (STD)', 'PM2.5 (STD)', 'PM10  (STD)', '>0.3um', '>0.5um', '>1.0um',
'>2.5um', '>5.0um', '>10um']
header_row = ','.join(headers)+'\n'

'''DS functions'''
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

def read_humiture():
	""" Reads SHT11 temperature and humidity"""
    with SHT1x(Data[i], sck[i], gpio_mode=GPIO.BOARD) as sensor:
        temp = sensor.read_temperature()
        humidity = sensor.read_humidity(temp)
        #dew_pt = sensor.calculate_dew_point(temp, humidity)
        return [temp, humidity]

def read_pm_line(_port):
	""" Reads PMS5003 values"""
    rv = b''
    while True:
        ch1 = _port.read()
        if ch1 == b'\x42':
            ch2 = _port.read()
            if ch2 == b'\x4d':
                rv += ch1 + ch2
                rv += _port.read(bytes2read)
                return rv

def read_all():
	""" Reads all sensors to list with timestamp"""
    row = []
    timestamp = datetime.now(timezone.utc)
    now= timestamp.strftime('%Y-%m-%d %H:%M:%S')
    row.append(now)
    '''Reads temp from DS sensor'''
    if len(device_files) != 0:
        for device_file in device_files:
            tempDS = read_temp()
            row.append(str(tempDS))
    else:
        row.append('')
        row.append('')
    '''Reads temp + humidity from SHT sensor'''
    for i in range(0, len(Data)):
        try:
            humiture = read_humiture()
            row.append(str(humiture[0]))
            row.append(str(humiture[1]))
            #row.append(str(dew_pt))
        except:
            row.append('')
            row.append('')
    ''' Reads PM sensor'''
    rcv = read_pm_line(port)
    for x,y in zip(evenbytes,oddbytes):
        try:
            value = rcv[x]*256 + rcv[y]
            row.append(str(value))
        except:
            row.append('')
    return [timestamp,row]

def write_all():
    ''' Writes to .csv'''
    current_time = read_all()[0]
    values_row = read_all()[1]
    today = current_time.strftime('%Y%m%d')
    filename = 'Test_' + today + '.csv'
    with open(filename,'a') as new_file:
        #check if file exists and writes headers
        if os.stat(filename).st_size ==0:
            new_file.write(header_row)
        else:
            wr = csv.writer(new_file)
            wr.writerow(values_row)
    print('Logged')

def upload_file():
    timestamp = read_all()[0]
    val_row = read_all()[1]
    str_val_row = str(','.join(val_row))
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("credentials.txt")
    if gauth.credentials is None:
        print('NONE')
    #    gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        print('expired')
        gauth.Refresh()
    else:
        print('authorize')
        gauth.Authorize()
    gauth.SaveCredentialsFile("credentials.txt")
    drive = GoogleDrive(gauth)

    tnow= timestamp.strftime('%Y%m%d_%H%M%S')
    fname = 'Test_' + tnow + '.csv'
    file1 = drive.CreateFile({'title': fname})
    file1.SetContentString(str_val_row)
    file1.Upload()
    print('uploaded')
    return
'''Starts scheduler'''
try:
    sched = BlockingScheduler(standalone=True)
    sched.add_job(write_all, 'interval', seconds=10)
    sched.add_job(upload_file, 'interval', seconds=20)
    sched.start()
except (KeyboardInterrupt):
    sched.shutdown(wait=False)
    print('Exiting nicely...')
