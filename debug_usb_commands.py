#!/usr/bin/env python3
"""
Debug script to verify the exact USB hub commands being sent
and check if the PORT_ON_CMDS are actually working correctly.
"""

import sys
import time

# Add the current directory to path to import our USB hub module
sys.path.append('.')

try:
    from usbhub_ascii import CoolGearUSBHub
except ImportError as e:
    print(f"Error importing USB hub module: {e}")
    sys.exit(1)

def debug_usb_commands():
    """Debug the exact commands being sent to the USB hub."""
    
    print("=== USB Hub Command Debug ===")
    print("Testing the exact commands that should control individual ports\n")
    
    # Initialize USB hub
    try:
        hub = CoolGearUSBHub('/dev/ttyUSB0')
        if not hub.ser or not hub.ser.is_open:
            print("ERROR: Could not connect to USB hub")
            return False
    except Exception as e:
        print(f"ERROR: Failed to initialize USB hub: {e}")
        return False
    
    # Show the PORT_ON_CMDS that should be working
    print("Expected PORT_ON_CMDS:")
    for port, cmd in hub.PORT_ON_CMDS.items():
        print(f"  Port {port}: {cmd}")
    
    print("\nStep 1: Start with ALL ports OFF")
    hub.all_off()
    time.sleep(1)
    print("All ports should be OFF now")
    input("Confirm all ports are OFF, then press Enter...")
    
    # Test each port individually
    for port in [1, 2, 3, 4]:
        print(f"\nStep {port+1}: Testing Port {port} individually")
        print(f"Command that will be sent: {hub.PORT_ON_CMDS[port]}")
        
        # Send the command using port_on method (the old way)
        print(f"Using old port_on({port}) method:")
        result = hub.port_on(port)
        if result:
            print(f"  Command sent successfully")
        else:
            print(f"  Command failed")
        
        time.sleep(2)
        response = input(f"Is ONLY port {port} ON? (y/n): ")
        if response.lower() != 'y':
            print(f"ERROR: Port {port} is not the only one ON!")
            print("This means the PORT_ON_CMDS are wrong")
        
        # Turn off this port before testing next one
        print("Turning OFF this port...")
        hub.port_off(port)
        time.sleep(1)
    
    print("\nStep 6: Test the new atomic method")
    for port in [1, 2, 3, 4]:
        print(f"\nAtomic test Port {port}:")
        print(f"Command: {hub.PORT_ON_CMDS[port]}")
        
        result = hub.set_single_port_on(port)
        if result:
            print(f"  Atomic command sent successfully")
        else:
            print(f"  Atomic command failed")
        
        time.sleep(2)
        response = input(f"Is ONLY port {port} ON? (y/n): ")
        if response.lower() != 'y':
            print(f"ERROR: Atomic method for port {port} failed!")
            print("Multiple ports are ON - the command is wrong")
    
    print("\nFinal cleanup...")
    hub.all_off()
    time.sleep(1)
    
    print("\n=== Debug Summary ===")
    print("If any port caused multiple ports to turn ON, then:")
    print("1. The PORT_ON_CMDS values are incorrect")
    print("2. We need to fix the command values")
    print("3. The USB hub might have different command expectations")

if __name__ == "__main__":
    debug_usb_commands()
