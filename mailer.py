""" Sends mail with internal IP address when connected to internet"""

import os
import requests
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

home_path = os.path.expanduser("~")
home = os.path.basename(home_path)

fromaddr = "orestis.raspberry@gmail.com"
recipients = ['orestispanago@gmail.com', 'orestispanago1@yahoo.com']
toaddr = ', '.join(recipients)
msg = MIMEMultipart()
msg['From'] = fromaddr
msg['To'] = toaddr
msg['Subject'] = home + " online!"

def connected_to_internet(url='http://www.google.com/', timeout=5):
    try:
        requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        print("No internet connection available.")
    return False

def mailer():
    msg.attach(MIMEText(body, 'plain'))
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "katipiomikro")
    text = msg.as_string()
    server.sendmail(fromaddr, recipients, text)
    server.quit()

while connected_to_internet() is not True:
    time.sleep(10)
else:
    ip = os.popen("hostname -I").readlines()
    body = 'Local IP: '+''.join(ip)
    mailer()
