#!/usr/bin/env python3
"""
Test script to verify atomic single-port control.
Tests that only one port is ever on at any given time during transitions.
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

def test_atomic_port_control():
    """Test that port transitions are atomic - only one port on at a time."""
    
    print("=== Testing Atomic Single Port Control ===")
    print("This test verifies that only one port is ever on during transitions\n")
    
    # Initialize USB hub
    try:
        hub = CoolGearUSBHub('/dev/ttyUSB0')
        if not hub.ser or not hub.ser.is_open:
            print("ERROR: Could not connect to USB hub")
            return False
    except Exception as e:
        print(f"ERROR: Failed to initialize USB hub: {e}")
        return False
    
    # Start with all ports off
    print("Step 1: Ensuring all ports are OFF")
    hub.all_off()
    time.sleep(1)
    print("All ports should be OFF now")
    input("Press Enter to continue to atomic port testing...")
    
    # Test atomic transitions between ports
    ports_to_test = [1, 2, 3, 4, 1, 3, 2, 4]  # Mix of transitions to test
    
    print(f"\nStep 2: Testing atomic port transitions")
    print("Watch the USB devices - only ONE should be on at any time")
    print("There should be NO brief moments where multiple ports are on\n")
    
    for i, port in enumerate(ports_to_test):
        print(f"Transition {i+1}: Setting ONLY port {port} ON (atomic operation)")
        
        # Use the new atomic method
        result = hub.set_single_port_on(port)
        
        if result:
            print(f"  -> Port {port} should now be the ONLY port ON")
        else:
            print(f"  -> ERROR: Failed to set port {port}")
        
        # Short pause to observe the state
        time.sleep(2)
        
        # Ask user to confirm only one port is on
        response = input(f"  Is ONLY port {port} ON (all others OFF)? (y/n/q to quit): ")
        if response.lower() == 'q':
            break
        elif response.lower() != 'y':
            print(f"  ERROR: Multiple ports detected during port {port} transition!")
            print("  This indicates the atomic control is not working properly.")
    
    # End test with all ports off
    print("\nStep 3: Final cleanup - turning all ports OFF")
    hub.all_off()
    time.sleep(1)
    print("Test complete - all ports should be OFF")
    
    print("\n=== Test Summary ===")
    print("If you saw multiple ports on at the same time during any transition,")
    print("then there is still an issue with atomic port control.")
    print("If only one port was ever on at a time, then the fix is working!")

if __name__ == "__main__":
    test_atomic_port_control()
