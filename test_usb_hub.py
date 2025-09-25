#[WARNING]/usr/bin/env python3
"""
USB Hub Channel Test Script
Tests all 4 USB hub channels to verify proper operation for Internet page functionality.
This script mimics the behavior of the Internet page radio button selections.
"""

import sys
import os
import time

# Add the USB hub controller path
sys.path.append("/home/tblank/code/tblank1024/rv/usbhub")

try:
    from usbhub_ctl_pi import CoolGearUSBHub
    print("[OK] Successfully imported CoolGearUSBHub")
except ImportError as e:
    print(f"[ERROR] Failed to import USB hub controller: {e}")
    print("Make sure the usbhub_ctl_pi.py file exists in /home/tblank/code/tblank1024/rv/usbhub/")
    sys.exit(1)

def test_usb_hub_channels():
    """Test all 4 USB hub channels systematically."""
    
    # Internet connection mappings (matching the Internet page)
    connections = {
        'Cellular': {'port': 1, 'wait_time': 15},
        'WiFi': {'port': 2, 'wait_time': 10}, 
        'Starlink': {'port': 3, 'wait_time': 20},
        'Wired': {'port': 4, 'wait_time': 8}
    }
    
    # Try common USB device paths
    possible_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    hub = None
    
    print("[INFO] Looking for USB hub on available ports...")
    for port in possible_ports:
        if os.path.exists(port):
            print(f"   Trying {port}...")
            try:
                hub = CoolGearUSBHub(port)
                if hub.ser and hub.ser.is_open:
                    print(f"[OK] Successfully connected to USB hub on {port}")
                    break
                else:
                    print(f"   Connection failed on {port}")
            except Exception as e:
                print(f"   Error on {port}: {e}")
                continue
    
    if not hub or not hub.ser or not hub.ser.is_open:
        print("[ERROR] Could not connect to USB hub on any port")
        print("Available ports:", [p for p in possible_ports if os.path.exists(p)])
        return False
    
    print(f"\n[INFO] Starting USB Hub Channel Test (v{hub.PROGRAM_VERSION})")
    print("="*60)
    
    # Test sequence: Turn off all, then test each channel individually
    success_count = 0
    total_tests = len(connections) + 1  # +1 for "all off" test
    
    try:
        # Test 1: All ports off (None selection)
        print("\n[INFO] Test 1: All ports OFF (None selection)")
        print("-" * 40)
        result = hub.all_off()
        if result:
            print("[OK] All ports turned OFF successfully")
            success_count += 1
        else:
            print("[ERROR] Failed to turn off all ports")
        
        time.sleep(2)  # Brief pause between tests
        
        # Test 2-5: Each individual port
        for connection_name, config in connections.items():
            port = config['port']
            wait_time = config['wait_time']
            
            print(f"\n[INFO] Test {port + 1}: {connection_name} (Port {port})")
            print("-" * 40)
            
            # First turn off all ports (simulate exclusive selection)
            print("  Step 1: Turning off all other ports...")
            hub.all_off()
            time.sleep(0.5)
            
            # Then turn on the target port
            print(f"  Step 2: Turning ON port {port} for {connection_name}...")
            result = hub.port_on(port)
            
            if result:
                print(f"[OK] Port {port} ({connection_name}) turned ON successfully")
                success_count += 1
                
                # Simulate the wait time that would happen in real usage
                print(f"  Step 3: Simulating {wait_time}s initialization wait...")
                for i in range(wait_time):
                    if i % 5 == 0 or i < 3 or i >= wait_time - 2:
                        print(f"    Waiting... {i+1}/{wait_time}s")
                    time.sleep(1)
                
                # Try to get status to verify port is on
                print("  Step 4: Checking port status...")
                status_cmd = f"GP\r"
                response = hub._execute_command(status_cmd)
                if response:
                    print(f"  [INFO] Status response: '{response}'")
                else:
                    print("  [WARNING] No status response (may be normal)")
                    
            else:
                print(f"[ERROR] Failed to turn ON port {port} ({connection_name})")
            
            time.sleep(1)  # Brief pause between tests
    
    except KeyboardInterrupt:
        print("\n[WARNING] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed with error: {e}")
    finally:
        # Clean up: Turn off all ports
        print("\n[INFO] Cleanup: Turning off all ports...")
        try:
            hub.all_off()
            print("[OK] Cleanup completed")
        except:
            print("[WARNING] Cleanup failed")
    
    # Test Results Summary
    print("\n" + "="*60)
    print("[INFO] TEST RESULTS SUMMARY")
    print("="*60)
    print(f"Tests passed: {success_count}/{total_tests}")
    print(f"Success rate: {(success_count/total_tests)[INFO]100:.1f}%")
    
    if success_count == total_tests:
        print("[OK] ALL TESTS PASSED[WARNING] USB Hub is ready for Internet page integration.")
        return True
    elif success_count > 0:
        print("[WARNING] PARTIAL SUCCESS: Some tests passed, check USB hub connections.")
        return False
    else:
        print("[ERROR] ALL TESTS FAILED: Check USB hub connection and power.")
        return False

def interactive_test():
    """Interactive mode for manual testing."""
    print("\n[INFO] INTERACTIVE TEST MODE")
    print("You can manually test individual ports or run the full automated test.")
    print("Commands:")
    print("  'auto' - Run automated test")
    print("  '1', '2', '3', '4' - Test specific port")
    print("  'off' - Turn all ports off")
    print("  'status' - Get hub status")
    print("  'exit' - Exit interactive mode")
    
    # Get hub connection (similar to main test)
    possible_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
    hub = None
    
    for port in possible_ports:
        if os.path.exists(port):
            try:
                hub = CoolGearUSBHub(port)
                if hub.ser and hub.ser.is_open:
                    print(f"Connected to hub on {port}")
                    break
            except:
                continue
    
    if not hub or not hub.ser or not hub.ser.is_open:
        print("[ERROR] Could not connect to USB hub")
        return
    
    while True:
        try:
            cmd = input("\nHub> ").strip().lower()
            
            if cmd == 'exit':
                break
            elif cmd == 'auto':
                test_usb_hub_channels()
            elif cmd == 'off':
                hub.all_off()
                print("All ports turned off")
            elif cmd == 'status':
                response = hub._execute_command("GP\r")
                print(f"Status: {response}")
            elif cmd in ['1', '2', '3', '4']:
                port = int(cmd)
                hub.all_off()
                time.sleep(0.5)
                hub.port_on(port)
                print(f"Port {port} turned on")
            else:
                print("Unknown command")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    print("[INFO] USB Hub Channel Test Script")
    print("This script tests the 4 USB channels used by the Internet page")
    
    if len(sys.argv) > 1 and sys.argv[1] == 'interactive':
        interactive_test()
    else:
        success = test_usb_hub_channels()
        sys.exit(0 if success else 1)
