# -*- coding: utf-8 -*-
"""
Notifications
-------------

Example showing how to add notifications to a characteristic and handle the responses.

Updated on 2019-07-03 by hbldh <henrik.blidh@gmail.com>

"""

from operator import truediv
import sys
import asyncio
import platform

from bleak import BleakClient
import atexit
import time

import logging

logging.basicConfig()
logging.getLogger('BLEAK_LOGGING').setLevel(logging.DEBUG)

#CONSTANTS
DEV_MAC1 = 'F8:33:31:56:ED:16'
DEV_MAC2 = 'F8:33:31:56:FB:8E'
CHARACTERISTIC_UUID = '0000ffe1-0000-1000-8000-00805f9b34fb'          #GATT Characteristic UUID

#variables
LastMessage = ""



def notification_handler_battery(sender, data):
    """Simple notification handler which prints the data received.
    Note data from device comes back as binary array of data representing the data
    in a BCD format seperated by commas.  The end of record termination is \r.
    Each return provides 20 bytes in the following format
    4 bytes - providing the battery voltage 13.50 (note the decimal point is assumed)
    1 byte  - comma
    3 bytes - current in amps +/- 10.5
    1 byte  - comma
    3 bytes - current in amps +/- 10.5
    1 byte  - comma
    3 bytes - Power in kW +/- 10.5
    1 byte  - comma
    3 bytes - Power in kW +/- 10.5
    ************  new record starts here
    1 byte  - comma
    2 bytes - Battery Temp in F (Not sure of neg values)
    1 byte  - comma
    2 bytes - BMS in F (Not sure of neg values)
    1 byte  - comma
    1 byte  - not sure of meaning values 0 to -2
    3 bytes - Percent battery full (0 - 100%)
    1 byte  - comma
    6 bytes - Status Code (all 0's is good)
    1 bytes - record termination char 0x0d CR
    ************  new record starts here
    1 byte  - record termination char 0x0a  LF
     """
    
    global LastMessage
    global fp

    if data[0] == 0x0a:          # end of complete record
        TimeString = str(time.time())
        print(TimeString + ","+ LastMessage)
        fp.write(TimeString + ","+ LastMessage)
        """
        print("Volt = " + LastMessage[0:4])
        print("Amp1 = " + LastMessage[5:8])
        print("Amp2 = " + LastMessage[9:12])
        print("Pwr1 = " + LastMessage[13:16])
        print("Pwr2 = " + LastMessage[17:20])
        print("Temp = " + LastMessage[21:23])
        print("BMS  = " + LastMessage[24:26])
        print("???  = " + LastMessage[27])
        print("Full = " + LastMessage[29:32])
        print("Stat = " + LastMessage[33:39])
        """
        LastMessage = ""
    else:
        LastMessage += data.decode("utf-8")

    # print("{0}: {1}".format(sender, data))
    """
    hexdata = data.hex()
    print(hexdata)
    strdata = data[0:4].decode('utf-8')    
    print(strdata)
    """
    
    
    


#deptricated original from example
async def main1(address, char_uuid):
    async with BleakClient(address) as client:
        print(f"Connectted: {client.is_connected}")
        await client.start_notify(char_uuid, notification_handler_battery)
        while True:
            await asyncio.sleep(5.0)
        print(f"Disconnecting: {client.is_connected}")
        await client.stop_notify(char_uuid)

        

async def OneClient(address1, char_uuid):  # need unique address and service address for each  todo
    global fp

    client1 = BleakClient(address1)
    await client1.connect()
    print(f"Connectted: {client1.is_connected}")

    try:
        await client1.start_notify(char_uuid, notification_handler_battery)

        while True:
            await asyncio.sleep(5.0)
    finally: 
        
        fp.close()
        print(f"Disconnecting: {client1.is_connected}")       
        await client1.stop_notify(char_uuid)
        await client1.disconnect()  
        print(f"Disconnect2: {client1.is_connected}")
        

async def TwoClient(address1, address2, char_uuid):  # need unique address and service address for each  todo
    client1 = BleakClient(address1)
    await client1.connect()
    print(f"Connectted: {client1.is_connected}")

    client2 = BleakClient(address2)
    await client2.connect()
    print(f"Connectted: {client2.is_connected}")

    try:
        await client1.start_notify(char_uuid, notification_handler_battery)
        await client2.start_notify(char_uuid, notification_handler_battery)

        while True:
            await asyncio.sleep(5.0)
    except KeyboardInterrupt:
        print("Caught KyBd interrupt")
    finally: 
        print(f"Disconnecting all clients")
        await client1.stop_notify(char_uuid)
        await client1.disconnect()  
        await client2.stop_notify(char_uuid)
        await client2.disconnect()  
        print(f"Disconnect:  Clients 1 & 2 connected?: {client1.is_connected} {client2.is_connected}")


if __name__ == "__main__":
    fp = open("batterylog.txt","w")
    asyncio.run( OneClient(DEV_MAC1,CHARACTERISTIC_UUID ) )
    # asyncio.run( main3(DEV_MAC1, DEV_MAC2,CHARACTERISTIC_UUID )