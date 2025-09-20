#!/usr/bin/env python3
"""
Simplified bat2mqtt.py - BLE to MQTT Bridge
Connects to BLE device via hci1 and publishes battery data to MQTT
Sequential operation without threads or subprocesses to avoid Docker duplicate output issues
"""

import asyncio
import json
import argparse
import time
import sys
import signal
from typing import Optional

import paho.mqtt.client as mqtt
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice


class BatteryMQTTBridge:
    def __init__(self, mqtt_broker: str = "localhost", mqtt_port: int = 1883, 
                 mqtt_topic: str = "RVC/BATTERY_STATUS", debug: int = 0):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.mqtt_topic = mqtt_topic
        self.debug = debug
        self.mqtt_client = None
        self.ble_device = None
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        if self.debug > 0:
            print(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def _setup_mqtt(self):
        """Setup MQTT client connection"""
        try:
            self.mqtt_client = mqtt.Client()
            self.mqtt_client.on_connect = self._on_mqtt_connect
            self.mqtt_client.on_disconnect = self._on_mqtt_disconnect
            
            if self.debug > 0:
                print(f"Connecting to MQTT broker {self.mqtt_broker}:{self.mqtt_port}")
            
            self.mqtt_client.connect(self.mqtt_broker, self.mqtt_port, 60)
            self.mqtt_client.loop_start()
            return True
            
        except Exception as e:
            print(f"Failed to connect to MQTT broker: {e}")
            return False
            
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            if self.debug > 0:
                print("Connected to MQTT broker successfully")
        else:
            print(f"Failed to connect to MQTT broker, result code: {rc}")
            
    def _on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        if self.debug > 0:
            print("Disconnected from MQTT broker")
            
    def _publish_mqtt(self, data: dict):
        """Publish data to MQTT with proper encoding handling"""
        try:
            # Handle encoding issues by ensuring all strings are properly encoded
            encoded_data = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Replace problematic characters like checkmarks with safe alternatives
                    encoded_data[key] = value.encode('utf-8', errors='replace').decode('utf-8')
                else:
                    encoded_data[key] = value
                    
            # Add timestamp
            encoded_data['timestamp'] = time.time()
            
            payload = json.dumps(encoded_data, ensure_ascii=False)
            
            if self.debug > 1:
                print(f"Publishing to {self.mqtt_topic}: {payload}")
                
            result = self.mqtt_client.publish(self.mqtt_topic, payload)
            
            if self.debug > 2:
                print(f"MQTT publish result: {result.rc}")
                
            return result.rc == 0
            
        except Exception as e:
            print(f"Error publishing to MQTT: {e}")
            return False
            
    async def _find_battery_device(self) -> Optional[BLEDevice]:
        """Find and return the BLE battery device"""
        if self.debug > 0:
            print("Scanning for BLE devices...")
            
        try:
            # Use hci1 adapter as specified
            devices = await BleakScanner.discover(adapter="hci1", timeout=10.0)
            
            if self.debug > 1:
                print(f"Found {len(devices)} BLE devices")
                
            # Look for battery-related devices (you may need to adjust this logic)
            for device in devices:
                if self.debug > 2:
                    print(f"Device: {device.name} - {device.address}")
                    
                # Simple heuristic - look for devices with "battery" in name or known battery service
                if device.name and any(keyword in device.name.lower() for keyword in ['battery', 'batt', 'power']):
                    if self.debug > 0:
                        print(f"Found potential battery device: {device.name} ({device.address})")
                    return device
                    
            # If no battery-specific device found, return the first available device for testing
            if devices:
                device = devices[0]
                if self.debug > 0:
                    print(f"Using first available device for testing: {device.name} ({device.address})")
                return device
                
            return None
            
        except Exception as e:
            print(f"Error scanning for BLE devices: {e}")
            return None
            
    async def _read_battery_data(self, client: BleakClient) -> Optional[dict]:
        """Read battery data from BLE device"""
        try:
            # Get device services and characteristics
            services = await client.get_services()
            
            battery_data = {
                "name": "BATTERY_STATUS",
                "instance": 1,
                "device_name": client.address,
                "status": "Connected"
            }
            
            # Look for battery service (UUID 0x180F) or other relevant services
            for service in services:
                if self.debug > 2:
                    print(f"Service: {service.uuid}")
                    
                for char in service.characteristics:
                    if self.debug > 2:
                        print(f"  Characteristic: {char.uuid} - Properties: {char.properties}")
                        
                    # Try to read battery level (UUID 0x2A19) or other relevant characteristics
                    if "read" in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            
                            # Basic battery level interpretation
                            if char.uuid.startswith("00002a19"):  # Battery Level
                                battery_data["State_of_charge"] = int.from_bytes(value, byteorder='little')
                                if self.debug > 1:
                                    print(f"Battery level: {battery_data['State_of_charge']}%")
                                    
                            # For demonstration, add raw data
                            elif len(value) > 0:
                                hex_value = value.hex()
                                battery_data[f"raw_data_{char.uuid[:8]}"] = hex_value
                                if self.debug > 2:
                                    print(f"Raw data from {char.uuid[:8]}: {hex_value}")
                                    
                        except Exception as e:
                            if self.debug > 2:
                                print(f"Could not read characteristic {char.uuid}: {e}")
                            continue
                            
            # Add some default values if no specific battery data was found
            if "State_of_charge" not in battery_data:
                battery_data["State_of_charge"] = 50  # Default value
                battery_data["DC_voltage"] = 12.0
                battery_data["DC_current"] = 0.0
                
            return battery_data
            
        except Exception as e:
            print(f"Error reading battery data: {e}")
            return None
            
    async def _process_ble_data(self):
        """Main BLE data processing loop"""
        while self.running:
            try:
                # Step 1: Find BLE device
                device = await self._find_battery_device()
                if not device:
                    print("No BLE device found, retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    continue
                    
                # Step 2: Connect to device
                if self.debug > 0:
                    print(f"Connecting to device {device.address}...")
                    
                async with BleakClient(device.address, adapter="hci1") as client:
                    if self.debug > 0:
                        print("Connected to BLE device")
                        
                    # Step 3: Main data reading loop
                    while self.running and client.is_connected:
                        # Wait for complete message (implement your specific message detection here)
                        await asyncio.sleep(1)  # Basic interval, adjust as needed
                        
                        # Step 4: Decode the message
                        battery_data = await self._read_battery_data(client)
                        
                        if battery_data:
                            # Step 5: Publish to MQTT
                            if self._publish_mqtt(battery_data):
                                if self.debug > 0:
                                    print("✓ Battery data published successfully")
                            else:
                                print("✗ Failed to publish battery data")
                        else:
                            if self.debug > 1:
                                print("No battery data received")
                                
                        # Step 6: Wait before next iteration
                        await asyncio.sleep(5)  # Adjust frequency as needed
                        
            except Exception as e:
                print(f"BLE processing error: {e}")
                if self.running:
                    print("Retrying in 10 seconds...")
                    await asyncio.sleep(10)
                    
    async def run(self):
        """Main application entry point"""
        print("Starting BLE to MQTT bridge...")
        
        # Setup MQTT connection
        if not self._setup_mqtt():
            print("Failed to setup MQTT connection")
            return False
            
        try:
            # Start BLE processing
            await self._process_ble_data()
            
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            # Cleanup
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            print("Bridge stopped")
            
        return True


def main():
    parser = argparse.ArgumentParser(description="BLE to MQTT Battery Bridge")
    parser.add_argument("-b", "--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("-p", "--port", default=1883, type=int, help="MQTT broker port") 
    parser.add_argument("-t", "--topic", default="RVC/BATTERY_STATUS", help="MQTT topic prefix")
    parser.add_argument("-d", "--debug", default=1, type=int, choices=[0, 1, 2, 3], 
                       help="Debug level (0=none, 1=basic, 2=verbose, 3=full)")
    
    args = parser.parse_args()
    
    # Create and run the bridge
    bridge = BatteryMQTTBridge(
        mqtt_broker=args.broker,
        mqtt_port=args.port, 
        mqtt_topic=args.topic,
        debug=args.debug
    )
    
    try:
        # Run the async main function
        asyncio.run(bridge.run())
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()