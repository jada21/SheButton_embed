#ACTUAL WORKING CODE - becoming large main code

from machine import Pin, UART, SoftI2C, ADC
import utime, time
from mlx90614_3 import MLX90614_I2C
from time import sleep_ms

# GPS Module UART Object Creation
gpsModule = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))
print("Connection details:")
print(gpsModule, "\n")

# Set up LoRa UART
Ltx_pin=Pin(16)
Lrx_pin=Pin(17)
lora_mod = UART(0, baudrate = 115200, tx=Ltx_pin, rx=Lrx_pin)
print("Connection details:")
print(lora_mod, "\n")

lora_mod.write("AT\r\n")
sleep_ms(200)
lora_mod.write("AT+ADDRESS=21\r\n")
sleep_ms(200)
lora_mod.write("AT+NETWORKID=3\r\n")
sleep_ms(200)
reply= lora_mod.read(15).decode('utf-8') #u have to read enough bytes!!
print(reply)

# Set up i2c for MLX
i2c = SoftI2C(scl = Pin(11), sda = Pin(10), freq = 100000)
irtemp = MLX90614_I2C(i2c, 0x5A)

# Set default timeout status
TIMEOUT = False

# Set up button specs
cancel_flag =0
sos_flag = 0
sos_btn = Pin(12, Pin.IN, Pin.PULL_UP)
cancel_btn = Pin(13, Pin.IN, Pin.PULL_UP)

def ISR_sos(sos_btn):                           #SOS interrupt service routine
    global sos_flag
    sos_flag = 1

def ISR_cancel(cancel_btn):
    global cancel_flag
    cancel_flag =1

sos_btn.irq(trigger=Pin.IRQ_FALLING, handler=ISR_sos)           #attaches ISR to button
cancel_btn.irq(trigger=Pin.IRQ_FALLING, handler=ISR_cancel)

#Setting up mic specs
mic_pin = ADC(28)
conFactor = 3.3/65536                   #pico has 16 Bits ADC with a quantization level of 4096, but for some reason we use 655356
speech = 3               #regular speech output is 2 V

# Set up vibrator
vib1 = Pin(4, mode=Pin.OUT, value = 0)
vib = Pin(18, mode=Pin.OUT, value = 0)

# Getting GPS coordinates function
def getGPSData(gpsModule):
    global TIMEOUT, dmsLatitude, dmsLongitude, dmsLat_for_conversion, dmsLong_for_conversion
   
    # Creating time limit for function with timeout 10 seconds from now
    timeout = time.time() + 10  

    while True:
        try:
            rawNmeaData = gpsModule.readline()
            # Check if the result is not None before decoding
            # NMEA sentences are encoded with ASCII characters therefore 
            # use UTF-8 decoding protocol to decode data
            # strip() removes whitespaces at beginning and end of string
            if rawNmeaData is not None:
                nmeaData = rawNmeaData.decode('utf-8').strip()
                print(nmeaData)
        
                # Check if the NMEA data starts with "$GPGGA" and Check if "GPRMC" is in string, if so ignore it
                if nmeaData.startswith("$GPGGA"):
                    if "$GPRMC" in nmeaData:
                        break
                    nmeaList = nmeaData.split(',')
                    
                    #Extracting UTC time:
                    utc_raw = str(nmeaList[1])
                    try:
                        utc_hours = utc_raw[0]+utc_raw[1]
                        utc_min = utc_raw[2]+utc_raw[3]
                        utc_sec = utc_raw[4]+utc_raw[5]
                        utc_time_str = utc_hours + ":" + utc_min + ":" + utc_sec
                        
                        dmsLatitude = nmeaList[2]
                        dmsLongitude = nmeaList[4]
                        print()
                        print("UTC time: ", utc_time_str)
                        print("DMS Latitude: ", dmsLatitude, nmeaList[3])
                        print("DMS Longitude: ", dmsLongitude, nmeaList[5])
                        print()
                        #attaching -ve sign where necessary:
                        if 'S' in nmeaList[3]:
                            dmsLat_for_conversion = '-'+dmsLatitude
                        else:
                            dmsLat_for_conversion = dmsLatitude
                        #print(dmsLat_for_conversion)
                        
                        if 'W' in nmeaList[5]:
                            dmsLong_for_conversion = '-'+dmsLongitude
                        else:
                            dmsLong_for_conversion = dmsLongitude
                        #print(dmsLong_for_conversion)
                        
                        #allows code to update DDlat and DDlong when DMSlat and DMSlong are correct,
                        #not just when GPGGA is interrupted by GPRMC:
                        if (dmsLatitude and dmsLongitude is not None):
                            break
                    except IndexError as e:
                        print("IndexError occurred:", e)
                    except Exception as e:
                        print("An error occurred:", e)

            if time.time() > timeout:
                TIMEOUT = True
                break
            utime.sleep_ms(500)

        except UnicodeError as e:
            print("UnicodeError occurred:")
            time.sleep(1)

# Converting decimal minutes seconds into decimal degrees function
def toDecDegree(dmsValue):
    try:
        dmsValueFloat = float(dmsValue)
        degrees = int(dmsValueFloat/100)
        minutes = float(dmsValueFloat-(degrees*100))
        ddValue = degrees + (minutes/60)
        return ddValue
    except ValueError as e:
        print("ValueError occurred:", e)
        return

# Lora Communication function
def loraComm(latstr, lngstr, tempstr):
    message= ("AT+SEND=22,30,"+ latstr +","+ lngstr +","+ tempstr +"\r\n")
    print(message)
    lora_mod.write(message)
    print("wrote message to lora ")
    sleep_ms(400)
        
# Main code loop
while True:
    #this is new part
    mic_read_raw = mic_pin.read_u16()
    mic_read = abs(mic_read_raw*conFactor)    

    if sos_flag ==1:                # or mic_read > speech:
        while True:
            sleep_ms(100)
            print("Calling gps function, top of main code loop")
            getGPSData(gpsModule)
            print("\nGet GPS data has broken out of loop")
            global dmsLat_for_conversion
            global dmsLong_for_conversion
            ddLatitude = toDecDegree(dmsLat_for_conversion)
            print("\nDMS LAT: ", dmsLatitude)
            print("\nDD LAT: ", ddLatitude)
            ddLongitude = toDecDegree(dmsLong_for_conversion)
            print("\nDMS LONG: ", dmsLongitude)
            print("\nDD LONG: ", ddLongitude, "\n")
            
            temp = irtemp.get_temperature(1)        #0 for ambient temp, 1 for object temp
            print("Temp = %.2f" %temp, "\n")
            loraComm(str(ddLatitude), str(ddLongitude), str(temp))
            sleep_ms(50)

            try:
                sleep_ms(200)
                if lora_mod.any():
                    reply = lora_mod.read()
                    reply_decoded = reply.decode('utf-8')
                    print("Received reply:", reply_decoded, "\n")
                    datasplit = reply_decoded.split(',')
                    try:
                        vib_status = datasplit[2]
                        print(vib_status)
                        if vib_status == '1':  # Compare with string '1'
                            vib1 = Pin(4, mode=Pin.OUT, value = 1)
                            vib = Pin(18, mode=Pin.OUT, value = 1)
                            sleep_ms(1000)
                            vib1 = Pin(4, mode=Pin.OUT, value = 0)
                            vib = Pin(18, mode=Pin.OUT, value = 0)
                            sleep_ms(1000)
                    except IndexError as e:
                        print("IndexError occurred:", e)
                    except Exception as e:
                        print("An error occurred:", e)
                else:
                    print("No reply received")
            except AttributeError as e:
                print("Attribute error:", e)

            if TIMEOUT:
                print("Request Timeout: No GPS data found")
                TIMEOUT = False

            sos_flag = 0
            if cancel_flag ==1:
                break
            time.sleep_ms(10)           # Debounce delay, code literally doesnt work without this idk
        print("IM FINE NVM\n")
        cancel_flag = 0                 # Reset cancel flag
        continue
    if cancel_flag ==1:
            print("IM FINE NVM\n")
            cancel_flag = 0             # Reset cancel flag