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

import logging

logging.basicConfig()
logging.getLogger('BLEAK_LOGGING').setLevel(logging.DEBUG)


DEV_MAC1 = 'F8:33:31:56:ED:16'
DEV_MAC2 = 'F8:33:31:56:FB:8E'
CHARACTERISTIC_UUID = '0000ffe1-0000-1000-8000-00805f9b34fb'          #GATT Characteristic UUID

# you can change these to match your device or override them from the command line


def notification_handler1(sender, data):
    """Simple notification handler which prints the data received."""
    print("{0}: {1}".format(sender, data))


#deptricated oringal from example
async def main1(address, char_uuid):
    async with BleakClient(address) as client:
        print(f"Connectted: {client.is_connected}")
        await client.start_notify(char_uuid, notification_handler1)
        while True:
            await asyncio.sleep(5.0)
        print(f"Disconnecting: {client.is_connected}")
        await client.stop_notify(char_uuid)

        

async def main2(address1, char_uuid):  # need unique address and service address for each  todo
    client1 = BleakClient(address1)
    await client1.connect()
    print(f"Connectted: {client1.is_connected}")

    try:
        await client1.start_notify(char_uuid, notification_handler1)

        while client1 is not None:
            await asyncio.sleep(5.0)
    finally: 
        print(f"Disconnecting: {client1.is_connected}")       
        await client1.stop_notify(char_uuid)
        await client1.disconnect()  
        while client1.is_connected:
            print(f"Disconn1: {client1.is_connected}")
            await asyncio.sleep(1)
        print(f"Discon2: {client1.is_connected}")
        


if __name__ == "__main__":
    asyncio.run( main2(DEV_MAC2,CHARACTERISTIC_UUID ) )