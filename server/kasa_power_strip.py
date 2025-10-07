# Completely Synchronous Kasa Smart Plug Power Strip HS300 controller
# This module provides a truly synchronous interface to Kasa HS300 devices
# by using subprocess calls to the kasa CLI tool instead of the async library

import json
import os
import subprocess
import time
from typing import Dict, List, Optional, Union


class KasaPowerStripError(Exception):
    """Exception raised for Kasa power strip communication errors."""
    pass


class KasaPowerStrip:
    """Completely synchronous controller for Kasa HS300 Smart Power Strip.
       
       This version uses the kasa CLI tool via subprocess to avoid all asyncio
       complications. All operations are truly blocking and synchronous.
       
       Features:
       - Individual outlet control (on/off/toggle)
       - Real-time power monitoring per outlet
       - Energy consumption tracking
       - No asyncio dependencies
    """
    
    def __init__(self, host: Optional[str] = None, timeout: int = 10):
        """
        Initialize the Kasa Power Strip controller.
        
        Args:
            host: IP address of the power strip (if None, will use environment variable)
            timeout: Command timeout in seconds (default: 10)
        """
        # Support environment variables for Docker configuration
        self.host = host or os.getenv('KASA_HOST')
        self.timeout = timeout
        self.device_info = None
        
        if not self.host:
            raise KasaPowerStripError("Host IP address is required. Set KASA_HOST environment variable or pass host parameter.")
    
    def _run_kasa_command(self, command_args: List[str], use_json: bool = True) -> Dict:
        """
        Run a kasa CLI command and return the JSON result.
        
        Args:
            command_args: List of command arguments to pass to kasa CLI
            use_json: Whether to use --json flag for structured output
            
        Returns:
            Dictionary containing the command result
            
        Raises:
            KasaPowerStripError: If command fails or times out
        """
        try:
            # Build the full command
            cmd = ['kasa', '--host', self.host]
            if use_json:
                cmd.append('--json')
            cmd.extend(command_args)
            
            # Run the command with timeout
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True
            )
            
            # Parse JSON output
            if result.stdout.strip():
                if use_json:
                    try:
                        return json.loads(result.stdout)
                    except json.JSONDecodeError as e:
                        raise KasaPowerStripError(f"Failed to parse JSON output: {e}")
                else:
                    # Return plain text wrapped in dict
                    return {"output": result.stdout.strip()}
            else:
                return {"success": True}
                
        except subprocess.TimeoutExpired:
            raise KasaPowerStripError(f"Command timed out after {self.timeout} seconds")
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            raise KasaPowerStripError(f"Kasa command failed: {error_msg}")
        except FileNotFoundError:
            raise KasaPowerStripError("kasa CLI tool not found. Please install python-kasa package.")
        except Exception as e:
            raise KasaPowerStripError(f"Unexpected error running kasa command: {e}")
    
    def connect(self) -> bool:
        """
        Connect to the power strip and get device information.
        
        Returns:
            True if connection successful
            
        Raises:
            KasaPowerStripError: If connection fails
        """
        print(f"🎯 Connecting to Kasa device at {self.host}...")
        
        try:
            # Get device state which also tests connectivity
            self.device_info = self._run_kasa_command(['state'])
            
            # Extract system info from JSON response
            system_info = self.device_info.get('system', {}).get('get_sysinfo', {})
            children = system_info.get('children', [])
            
            # Verify it's a power strip with children
            if not children:
                raise KasaPowerStripError("Device is not a power strip or has no outlets")
            
            outlet_count = len(children)
            device_alias = system_info.get('alias', 'Unknown Device')
            
            print(f"✅ Connected! Found {outlet_count} outlets")
            print(f"📱 Device: {device_alias}")
            
            # Print outlet summary
            for i, child in enumerate(children):
                alias = child.get('alias', f'Outlet {i}')
                state = '🟢 ON' if child.get('state', 0) == 1 else '🔴 OFF'
                print(f"   Outlet {i}: {alias} - {state}")
            
            return True
            
        except Exception as e:
            raise KasaPowerStripError(f"Failed to connect to device at {self.host}: {e}")
    
    def get_all_outlet_status(self) -> List[Dict[str, Union[int, str, bool]]]:
        """
        Get status of all outlets.
        
        Returns:
            List of dictionaries containing outlet information
        """
        if not self.device_info:
            self.connect()
        
        # Refresh device state
        current_state = self._run_kasa_command(['state'])
        system_info = current_state.get('system', {}).get('get_sysinfo', {})
        children = system_info.get('children', [])
        
        outlets = []
        for i, child in enumerate(children):
            outlets.append({
                'outlet_id': i,
                'alias': child.get('alias', f'Outlet {i}').strip(),
                'is_on': child.get('state', 0) == 1,
                'device_id': child.get('id', f'outlet_{i}')
            })
        
        return outlets
    
    def get_outlet_status(self, outlet_id: int) -> Dict[str, Union[int, str, bool]]:
        """
        Get status of a specific outlet.
        
        Args:
            outlet_id: The outlet ID (0-based index)
            
        Returns:
            Dictionary containing outlet information
            
        Raises:
            ValueError: If outlet_id is invalid
        """
        outlets = self.get_all_outlet_status()
        
        if not 0 <= outlet_id < len(outlets):
            raise ValueError(f"Outlet ID must be between 0 and {len(outlets) - 1}")
        
        return outlets[outlet_id]
    
    def turn_on_outlet(self, outlet_id: int) -> bool:
        """
        Turn on a specific outlet.
        
        Args:
            outlet_id: The outlet ID (0-based index)
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If outlet_id is invalid
            KasaPowerStripError: If command fails
        """
        # Verify outlet exists
        outlets = self.get_all_outlet_status()
        if not 0 <= outlet_id < len(outlets):
            raise ValueError(f"Outlet ID must be between 0 and {len(outlets) - 1}")
        
        # Use kasa CLI to turn on the specific child device
        try:
            self._run_kasa_command(['device', '--child-index', str(outlet_id), 'on'], use_json=False)
            print(f"✅ Turned ON outlet {outlet_id} ({outlets[outlet_id]['alias']})")
            return True
        except Exception as e:
            raise KasaPowerStripError(f"Failed to turn on outlet {outlet_id}: {e}")
    
    def turn_off_outlet(self, outlet_id: int) -> bool:
        """
        Turn off a specific outlet.
        
        Args:
            outlet_id: The outlet ID (0-based index)
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If outlet_id is invalid
            KasaPowerStripError: If command fails
        """
        # Verify outlet exists
        outlets = self.get_all_outlet_status()
        if not 0 <= outlet_id < len(outlets):
            raise ValueError(f"Outlet ID must be between 0 and {len(outlets) - 1}")
        
        # Use kasa CLI to turn off the specific child device
        try:
            self._run_kasa_command(['device', '--child-index', str(outlet_id), 'off'], use_json=False)
            print(f"⭕ Turned OFF outlet {outlet_id} ({outlets[outlet_id]['alias']})")
            return True
        except Exception as e:
            raise KasaPowerStripError(f"Failed to turn off outlet {outlet_id}: {e}")
    
    def toggle_outlet(self, outlet_id: int) -> bool:
        """
        Toggle a specific outlet (on->off or off->on).
        
        Args:
            outlet_id: The outlet ID (0-based index)
            
        Returns:
            True if successful
            
        Raises:
            ValueError: If outlet_id is invalid
            KasaPowerStripError: If command fails
        """
        current_status = self.get_outlet_status(outlet_id)
        
        if current_status['is_on']:
            return self.turn_off_outlet(outlet_id)
        else:
            return self.turn_on_outlet(outlet_id)
    
    def get_power_consumption(self, outlet_id: Optional[int] = None) -> Dict:
        """
        Get power consumption information by parsing device state output.
        
        Args:
            outlet_id: Specific outlet ID (0-based), or None for total device power
            
        Returns:
            Dictionary containing power consumption data with 'power_w' field
        """
        try:
            # Get device state which includes power information
            device_state = self._run_kasa_command(['state'], use_json=False)
            output = device_state.get('output', '')
            
            if outlet_id is not None:
                # Parse individual outlet power from the text output
                lines = output.split('\n')
                current_outlet_index = -1
                in_child_section = False
                
                for line in lines:
                    # Check if this line starts a new child device section
                    if line.strip().startswith('== ') and '(Socket for HS300' in line:
                        current_outlet_index += 1
                        in_child_section = (current_outlet_index == outlet_id)
                        continue
                    
                    # If we're in the target outlet section, look for current consumption
                    if in_child_section and 'Current consumption (current_consumption):' in line:
                        try:
                            # Extract power value (format: "        Current consumption (current_consumption): 13.0 W")
                            power_str = line.split(':')[-1].strip()  # Get "13.0 W"
                            power_value = float(power_str.split()[0])  # Get "13.0"
                            return {"power_w": power_value, "outlet_id": outlet_id}
                        except (ValueError, IndexError) as e:
                            print(f"⚠️  Error parsing power for outlet {outlet_id}: {e}")
                            continue
                
                # If we couldn't find the outlet or its power data
                return {"error": f"Could not find power data for outlet {outlet_id}", "power_w": 0}
            
            else:
                # Parse total device power consumption (main device section)
                lines = output.split('\n')
                for line in lines:
                    # Look for main device current consumption (not in a child section)
                    if ('Current consumption (current_consumption):' in line and 
                        not line.startswith('        ')):  # Main device line is not indented
                        try:
                            power_str = line.split(':')[-1].strip()
                            power_value = float(power_str.split()[0])
                            return {"power_w": power_value, "device_total": True}
                        except (ValueError, IndexError):
                            continue
                
                return {"error": "Could not parse total power consumption", "power_w": 0}
            
        except Exception as e:
            print(f"⚠️  Power consumption data not available: {e}")
            return {"error": str(e), "power_w": 0}
    
    def get_device_info(self) -> Dict:
        """
        Get detailed device information.
        
        Returns:
            Dictionary containing device details
        """
        if not self.device_info:
            self.connect()
        
        return self.device_info
    
    def test_all_outlets(self, delay_seconds: float = 2.0) -> Dict[int, bool]:
        """
        Test all outlets by toggling them on and off.
        
        Args:
            delay_seconds: Delay between operations
            
        Returns:
            Dictionary mapping outlet_id to success status
        """
        print("🧪 Starting outlet test sequence...")
        results = {}
        
        try:
            outlets = self.get_all_outlet_status()
            original_states = {i: outlet['is_on'] for i, outlet in enumerate(outlets)}
            
            for outlet_id in range(len(outlets)):
                print(f"\n🔌 Testing outlet {outlet_id} ({outlets[outlet_id]['alias']})...")
                
                try:
                    # Turn on
                    self.turn_on_outlet(outlet_id)
                    time.sleep(delay_seconds)
                    
                    # Turn off
                    self.turn_off_outlet(outlet_id)
                    time.sleep(delay_seconds)
                    
                    # Restore original state
                    if original_states[outlet_id]:
                        self.turn_on_outlet(outlet_id)
                    
                    results[outlet_id] = True
                    print(f"✅ Outlet {outlet_id} test passed")
                    
                except Exception as e:
                    results[outlet_id] = False
                    print(f"❌ Outlet {outlet_id} test failed: {e}")
            
            print(f"\n🏁 Test complete! {sum(results.values())}/{len(results)} outlets passed")
            return results
            
        except Exception as e:
            print(f"❌ Test sequence failed: {e}")
            return {}


# Convenience functions for quick testing
def quick_test(host: Optional[str] = None):
    """Quick test function to verify device connectivity and basic operations."""
    print("🚀 Starting Kasa Power Strip Quick Test...")
    
    try:
        kasa = KasaPowerStrip(host)
        kasa.connect()
        
        print("\n📊 Current outlet status:")
        outlets = kasa.get_all_outlet_status()
        for outlet in outlets:
            state = '🟢 ON' if outlet['is_on'] else '🔴 OFF'
            print(f"  {outlet['outlet_id']}: {outlet['alias']} - {state}")
        
        print("\n✅ Quick test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Quick test failed: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        host = sys.argv[1]
    else:
        host = os.getenv('KASA_HOST')
    
    if not host:
        print("Usage: python kasa_power_strip.py <host_ip>")
        print("Or set KASA_HOST environment variable")
        sys.exit(1)
    
    quick_test(host)
