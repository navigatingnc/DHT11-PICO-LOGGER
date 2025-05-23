import machine
import time
import dht
import sdcard
import os # uos is preferred in MicroPython for OS-like functions
import uos
import network # For WiFi
import uftplib # For FTP

# --- Configuration Parsing Function ---
def parse_config(file_path="/sd/config.ini"):
    """
    Parses a simple INI-like configuration file from the SD card.
    Expected format:
    [SECTION]
    KEY=VALUE
    """
    config = {}
    current_section = None
    try:
        with open(file_path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and line.endswith("]"):
                    current_section = line[1:-1].upper()
                elif "=" in line and current_section:
                    key, value = line.split("=", 1)
                    key = key.strip().upper()
                    value = value.strip()
                    if current_section == "WIFI":
                        config[f"WIFI_{key}"] = value
                    elif current_section == "FTP":
                        config[f"FTP_{key}"] = value
        
        # Basic validation for essential keys
        required_wifi = ['WIFI_SSID', 'WIFI_PASSWORD']
        required_ftp = ['FTP_HOST', 'FTP_USER', 'FTP_PASS']
        
        for k in required_wifi:
            if k not in config:
                print(f"Config Error: Missing {k} in [WIFI] section.")
                return None
        for k in required_ftp:
            if k not in config:
                print(f"Config Error: Missing {k} in [FTP] section.")
                return None
        # Optional FTP_REMOTEPATH, defaults to None if not present
        config.setdefault('FTP_REMOTEPATH', None)
        if config['FTP_REMOTEPATH'] == '': # Treat empty string as no path
            config['FTP_REMOTEPATH'] = None

        return config

    except OSError as e:
        print(f"Error reading config file '{file_path}': {e}")
        return None
    except Exception as e:
        print(f"Error parsing config file '{file_path}': {e}")
        return None

# --- Wi-Fi Connection Function ---
wlan = None # Global wlan object
def connect_wifi(ssid, password):
    global wlan
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("Wi-Fi already connected.")
        return True

    print(f"Connecting to Wi-Fi (SSID: {ssid})...")
    wlan.connect(ssid, password)

    # Wait for connection with a timeout
    max_wait = 15  # seconds
    while max_wait > 0:
        if wlan.isconnected():
            status = wlan.ifconfig()
            print(f"Wi-Fi connected successfully. IP: {status[0]}")
            return True
        max_wait -= 1
        print(f"Waiting for connection... {max_wait}s left. Status: {wlan.status()}")
        time.sleep(1)

    print("Wi-Fi connection failed.")
    wlan.active(False) # Turn off Wi-Fi to save power if connection failed
    return False

def disconnect_wifi():
    global wlan
    if wlan and wlan.isconnected():
        print("Disconnecting Wi-Fi...")
        wlan.disconnect()
        wlan.active(False)
        print("Wi-Fi disconnected.")
    elif wlan:
        wlan.active(False) # Ensure it's off if it wasn't connected but active
        print("Wi-Fi was not connected, ensured it is inactive.")


# --- FTP Upload Function ---
def upload_to_ftp(ftp_host, ftp_user, ftp_pass, local_file_path, remote_path=None):
    ftp = None
    try:
        print(f"FTP: Attempting to connect to {ftp_host}...")
        ftp = uftplib.FTP()
        ftp.connect(ftp_host, port=21) # Default FTP port
        ftp.login(ftp_user, ftp_pass)
        print("FTP: Connected and logged in.")

        if remote_path and remote_path.strip():
            try:
                print(f"FTP: Changing to remote directory: {remote_path}")
                ftp.cwd(remote_path)
            except Exception as e: # uftplib might raise generic Exception for cwd errors
                print(f"FTP: Error changing to remote directory '{remote_path}': {e}. Uploading to root.")
                # If cwd fails, proceed to upload to the current (root) directory

        remote_filename = local_file_path.split('/')[-1]
        
        print(f"FTP: Uploading '{local_file_path}' as '{remote_filename}'...")
        with open(local_file_path, 'rb') as f:
            ftp.storbinary(f'STOR {remote_filename}', f)
        print(f"FTP: File '{remote_filename}' uploaded successfully.")
        return True

    except OSError as e: # Catch network related errors like host not found
        print(f"FTP OS Error: {e}")
        return False
    except Exception as e: # uftplib can raise various errors, including login errors
        print(f"FTP Error: {e}")
        return False
    finally:
        if ftp:
            try:
                ftp.quit()
                print("FTP: Connection closed.")
            except Exception as e:
                print(f"FTP: Error closing connection: {e}")

# --- Initialize DHT11 sensor ---
dht_sensor = dht.DHT11(machine.Pin(15)) # Assuming GP15 for DHT11 data

# --- Initialize SD card ---
# Standard SPI pins for Pico: GP10 (SCK), GP11 (MOSI/COPI), GP12 (MISO/CIPO)
# CS pin can be any other available GPIO, e.g., GP13
spi = machine.SPI(1, baudrate=1000000, sck=machine.Pin(10), mosi=machine.Pin(11), miso=machine.Pin(12))
cs = machine.Pin(13, machine.Pin.OUT) 
sd = None
vfs = None
try:
    sd = sdcard.SDCard(spi, cs)
    vfs = uos.VfsFat(sd)
    uos.mount(vfs, "/sd")
    print("SD card mounted successfully at /sd")
except Exception as e:
    print(f"Error mounting SD card: {e}. Cannot proceed without SD card.")
    # Depending on desired behavior, you might want to stop the script or enter a safe mode.
    # For now, it will likely fail later if the logfile path is used.
    # Consider adding machine.reset() or a loop that prevents further execution.
    while True: time.sleep(5) # Halt execution

logfile = "/sd/dht11_log.csv"
config_file_on_sd = "/sd/config.ini"

# --- Load Configuration ---
ftp_config = None
if sd: # Only attempt to load config if SD card is mounted
    print(f"Attempting to load configuration from {config_file_on_sd}...")
    ftp_config = parse_config(config_file_on_sd)
    if ftp_config:
        print("Configuration loaded successfully.")
        # print(f"Config details: {ftp_config}") # For debugging
    else:
        print("Failed to load configuration. FTP uploads will be skipped.")

# --- Create CSV header if logfile doesn't exist ---
if sd and logfile not in uos.listdir("/sd"): # Check if logfile exists
    try:
        with open(logfile, "w") as f:
            f.write("timestamp,temperature,humidity\n")
        print(f"Created log file: {logfile}")
    except Exception as e:
        print(f"Error creating log file: {e}")


# --- Main Loop ---
while True:
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
        # Using simple time.ticks_ms() for timestamp as time.time() might not be set
        # For more accurate timestamps, network time sync would be needed.
        timestamp_ms = time.ticks_ms() 
        
        if sd: # Only log to SD if mounted
            try:
                with open(logfile, "a") as f:
                    f.write(f"{timestamp_ms},{temp},{hum}\n")
                print(f"Logged to SD: T={temp}C, H={hum}%")
            except Exception as e:
                print(f"Error writing to SD card log: {e}")
        else:
            print(f"SD card not available. Data not logged: T={temp}C, H={hum}%")

        # --- Wi-Fi and FTP Operations ---
        if ftp_config and sd: # Only attempt FTP if config is loaded and SD is available (for logfile)
            wifi_connected = connect_wifi(ftp_config['WIFI_SSID'], ftp_config['WIFI_PASSWORD'])
            
            if wifi_connected:
                upload_success = upload_to_ftp(
                    ftp_config['FTP_HOST'],
                    ftp_config['FTP_USER'],
                    ftp_config['FTP_PASS'],
                    logfile, # local file path on SD card
                    ftp_config.get('FTP_REMOTEPATH') # Use .get for safety, though parse_config ensures it
                )
                if upload_success:
                    print("FTP upload successful.")
                else:
                    print("FTP upload failed.")
                
                disconnect_wifi() # Disconnect Wi-Fi after attempt
            else:
                print("Wi-Fi connection failed. Skipping FTP upload.")
        elif not ftp_config:
            print("FTP configuration not loaded. Skipping FTP upload.")
        elif not sd:
            print("SD card not available. Skipping FTP upload.")
            
    except Exception as e:
        print(f"Main loop error: {e}")
        # Potentially add a small delay or specific recovery logic here
        # If DHT or other critical sensor fails, might need to reset or reinitialize.
        # For now, we just print the error and continue the loop.

    # Wait for the next logging interval
    # The prompt implies a 10-second interval from the original script.
    # Network operations can take time, so the actual interval might be longer.
    print("Waiting 10 seconds for next cycle...")
    time.sleep(10)