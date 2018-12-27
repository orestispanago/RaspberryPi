"""
Scrapes values from LAPUP weather station website
Logs them to .db file
Checks for out-of-range values
Checks for consecutive zeros
Mails them
"""

import re
import os
import time
from datetime import datetime, timezone
import sqlite3
from contextlib import closing
from requests import get
from requests.exceptions import RequestException
from bs4 import BeautifulSoup
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Quantity:
    """Meteorological quantity measured by  LAPUP weather station"""
    quantlist = []
    oor_values = {}

    def __init__(self, col, value, min_value, max_value):
        self.col = col
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        Quantity.quantlist.append(self)

    def get_oor(self):
        """ Stores out-of-range values for a quantity to oor_values dictionary"""
        if float(self.value) < self.min_value or float(self.value) > self.max_value:
            Quantity.oor_values[self.col] = self.value


def simple_get(url):
    """
    Attempts to get the content at `url` by making an HTTP GET request.
    If the content-type of response is some kind of HTML/XML, return the
    text content, otherwise return None.
    """
    try:
        with closing(get(url, stream=True)) as resp:
            if is_good_response(resp):
                return resp.content
            return None

    except RequestException as err:
        log_error('Error during requests to {0} : {1}'.format(url, str(err)))
        return None


def is_good_response(resp):
    """Returns True if the response seems to be HTML, False otherwise """
    content_type = resp.headers['Content-Type'].lower()
    return (resp.status_code == 200
            and content_type is not None
            and content_type.find('html') > -1)


def log_error(err):
    """This function just prints errors, but you can make it do anything """
    print(err)


def scrape():
    """Scrapes values from rows of first table from lapup website
    :rtype: list
    """
    raw_html = simple_get('http://mymeasurements.eu/u/lapup/meteo.php?lang=en')
    html = BeautifulSoup(raw_html, 'html.parser')
    rows = html.select('table')[0].text.split('\n')
    return [re.findall("\\d+\\.\\d+", rows[i])[0] for i in range(2, 10)]


def init_quantities(vals):
    """Creates Quantity objects"""
    Quantity('temp', vals[0], -2.0, 41.0)
    Quantity('hum', vals[1], 5.0, 100.0)
    Quantity('wd', vals[2], 0.0, 360.0)
    Quantity('ws', vals[3], 0.0, 75.0)
    Quantity('max_ws', vals[4], 0.0, 75.0)
    Quantity('precip', vals[5], 0.0, 40.0)
    Quantity('press', vals[6], 970.0, 1030.0)
    Quantity('press_asl', vals[7], 970.0, 1030.0)


def write_db(columns, values):
    """Writes values from website to .db file"""
    conn = sqlite3.connect('store.db')
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS meteo_params
              (utime DATETIME DEFAULT CURRENT_TIMESTAMP,
              {} TEXT, {} TEXT, {} TEXT, {} TEXT,
              {} TEXT, {} TEXT, {} TEXT, {} TEXT)'''.format(*columns))

    cur.execute('''INSERT INTO meteo_params VALUES
              (CURRENT_TIMESTAMP,
              {}, {}, {}, {},
              {}, {}, {}, {})'''.format(*values))
    conn.commit()
    conn.close()


def read_db():
    """Read last 5 values from .db file to data frame"""
    conn = sqlite3.connect('store.db')
    dataf = pd.read_sql_query('''SELECT * FROM
                           (SELECT * FROM meteo_params ORDER BY utime DESC LIMIT 5)
                           ORDER BY utime ASC''', conn, index_col='utime',
                              parse_dates=True)
    conn.commit()
    conn.close()
    return dataf


def get_oor_str():
    """Get out-of-range values"""
    for a in Quantity.quantlist:
        Quantity.get_oor(a)
    return ", ".join(("{}={}".format(*i) for i in Quantity.oor_values.items()))


def get_zeros():
    """Checks for consecutive zeros and returns their column names as list"""
    zero_col = []
    df = read_db()
    df = df.astype(float)
    df1 = df.drop(columns='precip')
    try:
        for column in df1:
            if all(df1[column][k] == 0 for k in range(5)):
                zero_col.append(column)
    except IndexError:
        print('Database does not have 5 rows yet')
        return None
    return zero_col


def send_mail(observation):
    """ Sends mail to multiple recipients if necessary"""
    fromaddr = "orestis.raspberry@gmail.com"
    recipients = ['orestis.panagopou@upatras.gr', 'athanarg@upatras.gr']
    toaddr = ', '.join(recipients)

    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "This is a message sent by my Python script"

    body = 'Please check http://mymeasurements.eu/u/lapup/meteo.php?lang=en\n' + observation
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "YourRaspberryMailPassword")
    text = msg.as_string()
    server.sendmail(fromaddr, recipients, text)
    server.quit()
    log_mails('sent_mails.txt',subject = observation)

def file_timestamp(fname):
    """Seconds since last modified 'sent_mails.txt' """
    return time.time() - os.path.getmtime(fname)


def log_mails(fname,subject=None):
    """Creates 'sent_mails.txt' if empty"""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
    with open(fname, 'a') as new_file:
        # check if file exists and writes headers
        if os.stat(fname).st_size == 0:
            new_file.write(timestamp + ', created' + '\n')
        if subject:
            new_file.write(timestamp + ', ' + subject + '\n')


# def log_mails(subject):
#     """ Logs sent mails to file"""
#     timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S %Z')
#     with open('sent_mails.txt', 'a') as new_file:
#         new_file.write(timestamp + ', ' + subject + '\n')


def main():

    values = scrape()  # Scrape values from website

    init_quantities(values)  # Create Quantity objects

    cols = [i.col for i in Quantity.quantlist]
    write_db(cols, values)  # Write to .db

    oor_str = get_oor_str()  # out-of-range values
    zero_col = get_zeros()  # Consecutive zeros columns

    log_mails('sent_mails.txt', subject=None)  # if it does not exist
    last_sent = file_timestamp('sent_mails.txt')  # Seconds

    if last_sent < 60.0 or last_sent > 86400:
        if oor_str:
            send_mail('Found out-of-range values: ' + oor_str)
        if zero_col:
            send_mail('Found 5 consecutive zeros in: ' + ', '.join(zero_col))

main()
