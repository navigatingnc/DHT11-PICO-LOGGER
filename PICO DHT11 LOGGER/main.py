import machine
import time
import dht
import sdcard
import os
import uos

# Initialize DHT11 on GPIO pin (e.g., GP15)
dht_sensor = dht.DHT11(machine.Pin(15))

# Initialize SPI and SD card
spi = machine.SPI(1, baudrate=1000000, sck=machine.Pin(10), mosi=machine.Pin(11), miso=machine.Pin(12))
cs = machine.Pin(13, machine.Pin.OUT)
sd = sdcard.SDCard(spi, cs)
vfs = uos.VfsFat(sd)
uos.mount(vfs, "/sd")

logfile = "/sd/dht11_log.csv"

# Create CSV header if file doesn't exist
if logfile not in uos.listdir("/sd"):
    with open(logfile, "w") as f:
        f.write("timestamp,temperature,humidity\n")

while True:
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        timestamp = time.time()
        
        with open(logfile, "a") as f:
            f.write(f"{timestamp},{temp},{hum}\n")
        
        print(f"Logged: T={temp}C, H={hum}%")
        
    except Exception as e:
        print("Error:", e)

    time.sleep(10)