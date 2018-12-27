""" Reads and prints Sensirion SHT1x temperature and humidity"""

from pi_sht1x import SHT1x
import RPi.GPIO as GPIO

GPIO.setwarnings(False)

data_pin = 3
sck_pin = 5 

with SHT1x(data_pin, sck_pin, gpio_mode=GPIO.BOARD) as sensor:
    temp = sensor.read_temperature()
    humidity = sensor.read_humidity(temp)
    print(temp, humidity)
