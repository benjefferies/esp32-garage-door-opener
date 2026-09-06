from machine import Pin
import time

p = Pin(2, Pin.OUT, value=0)
print("GPIO2 pulse test: 5 x 500ms HIGH")
time.sleep_ms(200)
for i in range(5):
    print("HIGH", i + 1)
    p.value(1)
    time.sleep_ms(500)
    p.value(0)
    print("LOW")
    time.sleep_ms(1500)
print("done, GPIO2 LOW")
while True:
    time.sleep(1)
