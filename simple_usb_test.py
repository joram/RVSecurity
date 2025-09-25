#!/usr/bin/env python3
"""
Simple USB Hub Channel Test - Visual Verification
Turns on each channel for 3 seconds, one at a time
"""
from usbhub_ascii import CoolGearUSBHub
import time

def simple_channel_test():
    """Test each USB channel for 3 seconds - visual verification"""
    print("=== Simple USB Hub Channel Test ===")
    
    try:
        hub = CoolGearUSBHub('/dev/ttyUSB0')
        
        if not hub.ser or not hub.ser.is_open:
            print("[ERROR] Could not connect to USB hub")
            return
        
        print("[OK] Connected to USB hub")
        
        # Start with all ports off
        print("\nStarting with all ports OFF...")
        hub.all_off()
        time.sleep(1)
        
        # Test each channel
        channels = [
            (1, "Cellular"),
            (2, "WiFi"), 
            (3, "Starlink"),
            (4, "Wired")
        ]
        
        for port, name in channels:
            print(f"\n--- Testing Port {port} ({name}) ---")
            print(f"Turning ON port {port}...")
            
            result = hub.port_on(port)
            if result:
                print(f"[OK] Port {port} ({name}) is ON - CHECK YOUR USB DEVICES")
                print("Waiting 3 seconds...")
                
                # Wait 3 seconds for visual verification
                for i in range(3, 0, -1):
                    print(f"  {i}...")
                    time.sleep(1)
                
                print(f"Turning OFF port {port}")
                hub.port_off(port)
                time.sleep(0.5)  # Brief pause between ports
            else:
                print(f"[ERROR] Failed to turn ON port {port}")
        
        print("\n=== Test Complete ===")
        print("All ports should now be OFF")
        
        # Final verification - all off
        hub.all_off()
        
        hub.ser.close()
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")

if __name__ == "__main__":
    print("This test will turn on each USB port for 3 seconds")
    print("Watch your USB devices to see which ones power on/off")
    print("Press Ctrl+C to stop if needed")
    print()
    
    try:
        simple_channel_test()
    except KeyboardInterrupt:
        print("\n[STOPPED] Test interrupted by user")
    except Exception as e:
        print(f"[ERROR] {e}")
