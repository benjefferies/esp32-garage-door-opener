from machine import Pin
import time

# C3 GPIOs. Active-low: pin sinks optocoupler cathode (anode on 3V3).
PINS = (2, 7, 3, 4, 5, 6, 10, 1, 0, 18, 19)

print("Active-LOW pulses (1.2s each). Watch the door.")
for n in PINS:
    p = Pin(n, Pin.OUT, value=1)
    print("LOW gpio", n)
    p.value(0)
    time.sleep_ms(1200)
    p.value(1)
    print("release", n)
    time.sleep_ms(800)

print("Active-HIGH pulses on GPIO2 and GPIO7")
for n in (2, 7):
    p = Pin(n, Pin.OUT, value=0)
    print("HIGH gpio", n)
    p.value(1)
    time.sleep_ms(1200)
    p.value(0)
    print("release", n)
    time.sleep_ms(800)

print("sweep done")
while True:
    time.sleep(1)
