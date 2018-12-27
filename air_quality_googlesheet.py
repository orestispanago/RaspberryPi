""" Reads PMS5003, appends values to last Googlesheet row 
Needs googlesheet.py and sensors.py modules
"""

import os,glob,csv
from datetime import datetime, timezone
import sensors
import googlesheet as gs
from apscheduler.schedulers.blocking import BlockingScheduler


launch_datetime1 = '2018-02-09 20:42:00'
launch_datetime2 = '2018-02-09 20:42:10'

headers = ['Time UTC', 'Temp','Temp_sh','hum','PM1.0(CF=1)', 'PM2.5(CF=1)',
           'PM10 (CF=1)', 'PM1.0 (STD)', 'PM2.5 (STD)', 'PM10  (STD)', '>0.3um',
           '>0.5um', '>1.0um', '>2.5um', '>5.0um', '>10um']

# reads all sensors
def read_all():
    timestamp = datetime.now(timezone.utc)
    now = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    today = timestamp.strftime('%Y%m%d')
    temp = sensors.read_temp()
    temp_hum = sensors.sensirion()
    ## read_pm() runs on infinite while ,do not call if sensor disconnected
    pm_list = sensors.read_pm()
    # adds datetime in the begining of pm_list
    row = [now] + [temp] + temp_hum + pm_list
    print(row)
    return [today, row]

# writes sensor values to csv
def write_csv():
    today, row = read_all()
    fpath = dirpath + user + '_' + today + '.csv'
    with open(fpath, 'a') as new_file:
        writer = csv.writer(new_file)
        if os.stat(fpath).st_size == 0:
            writer.writerow(headers)
        writer.writerow(row)

# reads last line from last csv and uploads to google sheet
def upload_line():
    csvlist = glob.glob(dirpath+"*.csv")
    csvlist.sort()
    with open(csvlist[-1], 'r') as readf:
        # reads lines in reversed order
        for line in reversed(list(csv.reader(readf))):
            break
    gs.append(sheetname,valrow=line)

'''main'''

# creates home/rz*/rz*_raw directory
userpath = os.path.expanduser("~")
user = os.path.basename(userpath)
dirpath = userpath + '/' + user + '_raw/'
dirname = os.path.basename(dirpath)
os.makedirs(dirpath, exist_ok=True)

# google sheet name
sheetname = user+'_10min'

# starts scheduler
try:
    sched = BlockingScheduler(standalone=True)
    sched.add_job(write_csv, 'interval', seconds=20, start_date=launch_datetime1)
    try:
        gs.check(sheetname,header=headers)
        sched.add_job(upload_line, 'interval', seconds=20, start_date=launch_datetime2)
    except:
        pass
    sched.start()
except (KeyboardInterrupt):
    sched.shutdown(wait=False)
    print('\nExiting...')
