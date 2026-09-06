from machine import Pin
import time

# OC1 anode = GPIO7. 5s on / 5s off so you can watch the door and a voltmeter.
p = Pin(7, Pin.OUT, value=0)
while True:
    print("GPIO7 HIGH 5s")
    p.value(1)
    time.sleep(5)
    print("GPIO7 LOW 5s")
    p.value(0)
    time.sleep(5)
