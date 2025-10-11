# Completely Synchronous Kasa Smart Plug Power Strip HS300 controller
# This module provides a truly synchronous interface to Kasa HS300 devices
# by using subprocess calls to the kasa CLI tool instead of the async library

import json
import os
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Union, Tuple


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
    
    def __init__(self, host: Optional[str] = None, timeout: int = 8):
        """
        Initialize the Kasa Power Strip controller.
        
        Args:
            host: IP address of the power strip (if None, will use environment variable)
            timeout: Command timeout in seconds (default: 8, balanced for device discovery)
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
            # Build the full command - use full path to kasa CLI if available
            kasa_cmd = shutil.which('kasa')
            if not kasa_cmd:
                # Try the virtual environment path
                venv_kasa = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'venv', 'bin', 'kasa')
                if os.path.exists(venv_kasa):
                    kasa_cmd = venv_kasa
                else:
                    kasa_cmd = 'kasa'  # fallback to PATH lookup
            
            cmd = [kasa_cmd, '--host', self.host]
            if use_json:
                cmd.append('--json')
            cmd.extend(command_args)
            
            # Run the command with timeout and environment modifications to reduce warnings
            env = os.environ.copy()
            env['PYTHONWARNINGS'] = 'ignore'  # Suppress Python warnings including asyncio
            env['PYTHONIOENCODING'] = 'utf-8'  # Ensure consistent encoding
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=True,
                encoding='utf-8',
                errors='replace',  # Replace problematic characters instead of failing
                env=env  # Use modified environment
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
            # Filter out aiohttp connection warnings that clutter the error messages
            if error_msg and ('ERROR:asyncio:Unclosed' in error_msg or 'aiohttp' in error_msg):
                # Extract just the relevant error info, skip the aiohttp spam
                lines = error_msg.split('\n')
                filtered_lines = [line for line in lines if not ('ERROR:asyncio:Unclosed' in line or 
                                                               'client_session:' in line or 
                                                               'connector:' in line or
                                                               'connections:' in line)]
                error_msg = '\n'.join(filtered_lines).strip()
                if not error_msg:
                    error_msg = "Kasa communication error (connection issues filtered)"
            raise KasaPowerStripError(f"Kasa command failed: {error_msg}")
        except FileNotFoundError:
            raise KasaPowerStripError("kasa CLI tool not found. Please install python-kasa package.")
        except Exception as e:
            raise KasaPowerStripError(f"Unexpected error running kasa command: {e}")
    
    def connect(self, verbose: bool = True) -> bool:
        """
        Connect to the power strip and get device information.
        
        Args:
            verbose: Whether to print connection details
        
        Returns:
            True if connection successful
            
        Raises:
            KasaPowerStripError: If connection fails
        """
        if verbose:
            print(f"Connecting to Kasa device at {self.host}...")
        
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
            
            if verbose:
                print(f"SUCCESS: Connected! Found {outlet_count} outlets")
                print(f"Device: {device_alias}")
                
                # Print outlet summary
                for i, child in enumerate(children):
                    alias = child.get('alias', f'Outlet {i}')
                    state = 'ON' if child.get('state', 0) == 1 else 'OFF'
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
            self.connect(verbose=False)
        
        # Refresh device state
        current_state = self._run_kasa_command(['state'])
        system_info = current_state.get('system', {}).get('get_sysinfo', {})
        children = system_info.get('children', [])
        
        outlets = []
        for i, child in enumerate(children):
            # Sanitize alias to remove problematic Unicode characters
            raw_alias = child.get('alias', f'Outlet {i}')
            try:
                # Try to encode/decode to clean up any problematic characters
                clean_alias = raw_alias.encode('ascii', errors='ignore').decode('ascii').strip()
                if not clean_alias:  # If nothing left after sanitization, use default
                    clean_alias = f'Outlet {i+1}'
            except:
                clean_alias = f'Outlet {i+1}'
                
            outlets.append({
                'outlet_id': i,
                'alias': clean_alias,
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
        # Basic validation without expensive network call
        if not 0 <= outlet_id <= 5:  # HS300 has 6 outlets (0-5)
            raise ValueError(f"Outlet ID must be between 0 and 5")
        
        # Use kasa CLI to turn on the specific child device directly
        try:
            self._run_kasa_command(['device', '--child-index', str(outlet_id), 'on'], use_json=False)
            print(f"SUCCESS: Turned ON port {outlet_id + 1}")
            return True
        except Exception as e:
            # If it fails, it might be because outlet doesn't exist or network issue
            error_msg = str(e)
            if "child" in error_msg.lower() or "index" in error_msg.lower():
                raise ValueError(f"Invalid outlet ID {outlet_id} - outlet may not exist")
            else:
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
        # Basic validation without expensive network call
        if not 0 <= outlet_id <= 5:  # HS300 has 6 outlets (0-5)
            raise ValueError(f"Outlet ID must be between 0 and 5")
        
        # Use kasa CLI to turn off the specific child device directly
        try:
            self._run_kasa_command(['device', '--child-index', str(outlet_id), 'off'], use_json=False)
            print(f"SUCCESS: Turned OFF port {outlet_id + 1}")
            return True
        except Exception as e:
            # If it fails, it might be because outlet doesn't exist or network issue
            error_msg = str(e)
            if "child" in error_msg.lower() or "index" in error_msg.lower():
                raise ValueError(f"Invalid outlet ID {outlet_id} - outlet may not exist")
            else:
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
    
    def get_all_outlet_status_with_power(self) -> Tuple[List[Dict[str, Union[int, str, bool, float]]], float]:
        """
        Get status and power consumption of all outlets in a single call.
        
        Returns:
            Tuple of (outlets_list, total_power)
        """
        # Get device state text output - contains both status and power info
        device_state = self._run_kasa_command(['state'], use_json=False)
        output = device_state.get('output', '')
        lines = output.split('\n')
        
        outlets = []
        power_data = {}
        total_power = 0
        current_outlet_index = -1
        current_outlet_alias = ""
        current_outlet_state = False
        in_child_section = False
        
        for line in lines:
            line = line.strip()
            
            # Check if this line starts a new child device section
            if line.startswith('== ') and '(Socket for HS300' in line:
                current_outlet_index += 1
                in_child_section = True
                # Extract alias from the header line
                # Format: "== Outlet Name (Socket for HS300(..."
                if ' (' in line:
                    current_outlet_alias = line.split(' (')[0].replace('== ', '')
                else:
                    current_outlet_alias = f'Outlet {current_outlet_index + 1}'
                continue
            
            # Look for device state in child sections
            if in_child_section and 'State (state):' in line:
                state_str = line.split(':')[-1].strip()
                current_outlet_state = (state_str.lower() == 'true')
                continue
            
            # Look for current consumption lines
            if 'Current consumption (current_consumption):' in line:
                try:
                    power_str = line.split(':')[-1].strip()
                    power_value = float(power_str.split()[0])
                    
                    if in_child_section and current_outlet_index >= 0:
                        # Store power data and create outlet record
                        power_data[current_outlet_index] = power_value
                        
                        # Clean up alias
                        try:
                            clean_alias = current_outlet_alias.encode('ascii', errors='ignore').decode('ascii').strip()
                            if not clean_alias:
                                clean_alias = f'Outlet {current_outlet_index + 1}'
                        except:
                            clean_alias = f'Outlet {current_outlet_index + 1}'
                        
                        outlets.append({
                            'outlet_id': current_outlet_index,
                            'alias': clean_alias,
                            'is_on': current_outlet_state,
                            'device_id': f'outlet_{current_outlet_index}',
                            'power_w': power_value
                        })
                        
                        in_child_section = False
                    elif not line.startswith('        '):
                        # This is the main device total (not indented)
                        total_power = power_value
                except (ValueError, IndexError):
                    continue
        
        return outlets, total_power
    
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
                            print(f"WARNING: Error parsing power for outlet {outlet_id}: {e}")
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
            print(f"WARNING: Power consumption data not available: {e}")
            return {"error": str(e), "power_w": 0}
    
    def get_device_info(self) -> Dict:
        """
        Get detailed device information.
        
        Returns:
            Dictionary containing device details
        """
        if not self.device_info:
            self.connect(verbose=False)
        
        return self.device_info
    
    def test_connectivity(self) -> bool:
        """
        Test connectivity to the device without verbose output.
        
        Returns:
            True if device responds, False otherwise
        """
        try:
            self._run_kasa_command(['state'])
            return True
        except Exception:
            return False
    
    def test_all_outlets(self, delay_seconds: float = 2.0) -> Dict[int, bool]:
        """
        Test all outlets by toggling them on and off.
        
        Args:
            delay_seconds: Delay between operations
            
        Returns:
            Dictionary mapping outlet_id to success status
        """
        print("Starting outlet test sequence...")
        results = {}
        
        try:
            outlets = self.get_all_outlet_status()
            original_states = {i: outlet['is_on'] for i, outlet in enumerate(outlets)}
            
            for outlet_id in range(len(outlets)):
                print(f"\nTesting outlet {outlet_id} ({outlets[outlet_id]['alias']})...")
                
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
                    print(f"SUCCESS: Outlet {outlet_id} test passed")
                    
                except Exception as e:
                    results[outlet_id] = False
                    print(f"ERROR: Outlet {outlet_id} test failed: {e}")
            
            print(f"\nTest complete! {sum(results.values())}/{len(results)} outlets passed")
            return results
            
        except Exception as e:
            print(f"ERROR: Test sequence failed: {e}")
            return {}


# Convenience functions for quick testing
def quick_test(host: Optional[str] = None):
    """Quick test function to verify device connectivity and basic operations."""
    print("Starting Kasa Power Strip Quick Test...")
    
    try:
        kasa = KasaPowerStrip(host)
        kasa.connect()
        
        print("\nCurrent outlet status:")
        outlets = kasa.get_all_outlet_status()
        for outlet in outlets:
            state = 'ON' if outlet['is_on'] else 'OFF'
            print(f"  {outlet['outlet_id']}: {outlet['alias']} - {state}")
        
        print("\nSUCCESS: Quick test completed successfully!")
        return True
        
    except Exception as e:
        print(f"ERROR: Quick test failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    import argparse
    
    def print_usage():
        """Print usage information."""
        print("Usage:")
        print("  python kasa_power_strip.py <host_ip> p<port> on|off")
        print("  python kasa_power_strip.py <host_ip> status")
        print("")
        print("Examples:")
        print("  python kasa_power_strip.py 192.168.1.100 p1 on     # Turn on port 1")
        print("  python kasa_power_strip.py 192.168.1.100 p3 off    # Turn off port 3")
        print("  python kasa_power_strip.py 192.168.1.100 status    # Show all port status")
        print("")
        print("Or set KASA_HOST environment variable and omit host_ip:")
        print("  python kasa_power_strip.py p2 on")
        print("  python kasa_power_strip.py status")
    
    def main():
        """Main command-line interface."""
        args = sys.argv[1:]
        
        # Determine if first argument is host IP
        host = None
        command_args = args
        
        if len(args) >= 1:
            # Check if first arg looks like an IP address (contains dots)
            if '.' in args[0] and not args[0].startswith('p'):
                host = args[0]
                command_args = args[1:]
            else:
                # Try to get host from environment
                host = os.getenv('KASA_HOST')
        
        if not host:
            print("ERROR: Host IP address required")
            print_usage()
            sys.exit(1)
        
        if len(command_args) == 0:
            print("ERROR: Command required")
            print_usage()
            sys.exit(1)
        
        command = command_args[0].lower()
        
        # Validate port commands before connecting
        if command.startswith('p') and command != 'status':
            if len(command_args) < 2:
                print("ERROR: Port command requires action (on/off)")
                print_usage()
                sys.exit(1)
            
            try:
                port_str = command[1:]  # Remove 'p' prefix
                port_num = int(port_str)
                
                if not 1 <= port_num <= 6:
                    print("ERROR: Port number must be between 1 and 6")
                    sys.exit(1)
                    
                action = command_args[1].lower()
                if action not in ['on', 'off']:
                    print(f"ERROR: Invalid action '{action}'. Use 'on' or 'off'")
                    sys.exit(1)
                    
            except ValueError:
                print(f"ERROR: Invalid port number '{port_str}'. Use p1, p2, p3, p4, p5, or p6")
                sys.exit(1)
        
        try:
            kasa = KasaPowerStrip(host)
            
            if command == 'status':
                # Connect quietly for status command
                kasa.connect(verbose=False)
                # Show status of all ports
                print("Port Status and Power Usage:")
                print("-" * 40)
                
                # Get all status and power data in a single call
                outlets, total_power = kasa.get_all_outlet_status_with_power()
                
                for outlet in outlets:
                    port_num = outlet['outlet_id'] + 1  # Convert to 1-based
                    status = 'ON' if outlet['is_on'] else 'OFF'
                    alias = outlet['alias']
                    power_w = outlet['power_w']
                    
                    print(f"Port {port_num}: {status:3} | {power_w:6.1f}W | {alias}")
                
                # Show total power consumption
                print("-" * 40)
                print(f"Total:     | {total_power:6.1f}W |")
                
            elif command.startswith('p'):
                # Port control command (p1, p2, etc.) - already validated above
                # Skip connection for speed - go directly to control
                port_str = command[1:]
                port_num = int(port_str)
                outlet_id = port_num - 1  # Convert to 0-based index
                action = command_args[1].lower()
                
                if action == 'on':
                    kasa.turn_on_outlet(outlet_id)
                elif action == 'off':
                    kasa.turn_off_outlet(outlet_id)
            else:
                print(f"ERROR: Unknown command '{command}'")
                print_usage()
                sys.exit(1)
                
        except KasaPowerStripError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Unexpected error: {e}")
            sys.exit(1)
    
    main()
