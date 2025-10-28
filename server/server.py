#!/usr/bin/env python3
import threading
import uvicorn
import os
import subprocess
import tempfile
import sys
import time
import socket
import requests
import json
import shutil
import signal
import atexit
import logging
# Initialize alarm-related global variables
alarm_mqtt_available = False

# Import alarm system from the rv/alarm directory (optional)
try:
    sys.path.append('/home/tblank/code/tblank1024/rv/alarm')
    import alarm
    ALARM_AVAILABLE = True
    print("Alarm system module loaded successfully")
except ImportError as e:
    print(f"Alarm system not available: {e}")
    print("Web alarm buttons will work for state tracking only")
    ALARM_AVAILABLE = False
    alarm = None
    # Check if we should use MQTT for alarm communication
    alarm_mqtt_available = True
    print("Will attempt MQTT communication with alarm container")
from rvglue import MQTTClient
import rvglue
from typing import Annotated
from kasa_power_strip import KasaPowerStrip, KasaPowerStripError
from usb_modem_manager import usb_modem_manager

from fastapi import FastAPI, Body
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles
from starlette.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import random
from server_calcs import *
from server_calcs import constants



app = FastAPI()
try:
    index_content = open("build/index.html").read()
except FileNotFoundError:
    index_content = "<html><body><h1>RV Security Server Running</h1><p>Build the client first with 'make build'</p></body></html>"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/power")
@app.get("/wifi")
@app.get("/internet")
@app.get("/debug")
async def index():
    return Response(index_content)

bike_alarm_state = False
interior_alarm_state = False

# Initialize alarm system
alarm_system = None
alarm_thread = None
alarm_thread_stop_event = None

# Internet Connection State Management
current_internet_connection = "none"  # Tracks current connection: "none", "cellular", "wifi", "starlink", "wired"

# Synology scheduled shutdown management
scheduled_shutdown_timestamp = None
shutdown_timer = None

def execute_scheduled_shutdown():
    """Execute the scheduled shutdown of Synology NAS"""
    global scheduled_shutdown_timestamp, shutdown_timer
    print("Executing scheduled Synology shutdown...")
    try:
        # Call the actual shutdown command
        import subprocess
        server_dir = os.path.dirname(os.path.abspath(__file__))
        password_file = os.path.join(server_dir, 'synology-password.json')
        cmd = ['python', 'synology_nas_controller.py', '--power-off', '--force', '--config', password_file]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=server_dir)
        
        if result.returncode == 0:
            print("Scheduled shutdown completed successfully")
        else:
            print(f"Scheduled shutdown failed: {result.stderr}")
    except Exception as e:
        print(f"Error during scheduled shutdown: {e}")
    finally:
        # Clear the scheduled time and timer
        scheduled_shutdown_timestamp = None
        shutdown_timer = None

def cancel_shutdown_timer():
    """Cancel any existing shutdown timer"""
    global shutdown_timer
    if shutdown_timer is not None:
        shutdown_timer.cancel()
        shutdown_timer = None

def schedule_shutdown_timer(delay_seconds):
    """Schedule a shutdown timer for the specified delay"""
    global shutdown_timer
    # Cancel any existing timer first
    cancel_shutdown_timer()
    # Create new timer
    shutdown_timer = threading.Timer(delay_seconds, execute_scheduled_shutdown)
    shutdown_timer.start()
    print(f"Scheduled shutdown timer set for {delay_seconds} seconds")

def initialize_alarm_system():
    """Initialize the alarm system with error handling"""
    global alarm_system, alarm_thread, alarm_thread_stop_event, alarm_mqtt_available
    
    # First check if we have direct alarm module access
    if ALARM_AVAILABLE and alarm is not None:
        try:
            debug_level = 0  # Set to 0 for normal operation, 1 for debug
            alarm_system = alarm.Alarm(debug_level)
            print("Alarm system initialized successfully (direct GPIO)")
            
            # Start the alarm monitoring thread
            alarm_thread_stop_event = threading.Event()
            alarm_thread = threading.Thread(target=alarm_monitoring_loop, daemon=True)
            alarm_thread.start()
            print("Alarm monitoring thread started")
            
            return True
        except Exception as e:
            print(f"Warning: Could not initialize direct GPIO alarm system: {e}")
            alarm_system = None
    
    # If direct GPIO failed, check if MQTT communication is available
    if alarm_mqtt_available:
        print("Direct GPIO alarm not available, using MQTT communication")
        print("Web alarm buttons will control physical alarms via MQTT")
        alarm_system = None  # Make sure it's None for MQTT mode
        return True
    else:
        print("No alarm system available - web alarm buttons will work for state tracking only")
        alarm_system = None
        return False

def alarm_monitoring_loop():
    """Background thread function that runs the alarm system monitoring loop"""
    global alarm_system, alarm_thread_stop_event
    
    if alarm_system is None:
        print("No direct alarm system available, monitoring loop not started")
        return
    
    print("Starting alarm monitoring loop in background thread")
    
    while not alarm_thread_stop_event.is_set():
        try:
            # Run one iteration of the alarm monitoring
            if alarm_system.debuglevel == 10:
                alarm_system._InternalTest()
            else:
                if alarm_system.InteriorState == alarm.States.OFF and alarm_system.BikeState == alarm.States.OFF and alarm_system.LoopCount > 10000:
                    # Don't let the LoopCount get too big
                    alarm_system.LoopCount = 1      
                else:
                    alarm_system.LoopCount += 1
                    
                alarm_system.LoopTime = time.time()
                alarm_system._check_buttons()    
                alarm_system._check_bike_wire()
                alarm_system._check_interior()
                alarm_system._update_timed_transitions()
                alarm_system._display()
                
                # Sync physical alarm states with web interface
                sync_alarm_states()
                
            # Sleep between iterations
            time.sleep(alarm_system.LOOPDELAY)
            
        except Exception as e:
            print(f"Error in alarm monitoring loop: {e}")
            time.sleep(1)  # Sleep longer on error to prevent spam
    
    print("Alarm monitoring loop stopped")

def sync_alarm_states():
    """Synchronize physical alarm states with web interface state variables"""
    global alarm_system, bike_alarm_state, interior_alarm_state
    
    if alarm_system is None or alarm is None:
        return
    
    # Convert physical alarm states to boolean for web interface
    # Physical alarm is considered "on" if it's in STARTING, ON, TRIGDELAY, TRIGGERED, or SILENCED states
    active_states = [alarm.States.STARTING, alarm.States.ON, alarm.States.TRIGDELAY, 
                    alarm.States.TRIGGERED, alarm.States.SILENCED]
    
    new_bike_state = alarm_system.BikeState in active_states
    new_interior_state = alarm_system.InteriorState in active_states
    
    # Update web interface states if they changed
    if new_bike_state != bike_alarm_state:
        bike_alarm_state = new_bike_state
        print(f"Physical bike alarm state changed to: {'ON' if new_bike_state else 'OFF'}")
    
    if new_interior_state != interior_alarm_state:
        interior_alarm_state = new_interior_state
        print(f"Physical interior alarm state changed to: {'ON' if new_interior_state else 'OFF'}")

def cleanup_alarm_system():
    """Clean up alarm system and stop monitoring thread"""
    global alarm_system, alarm_thread, alarm_thread_stop_event
    
    if alarm_thread_stop_event is not None:
        print("Stopping alarm monitoring thread...")
        alarm_thread_stop_event.set()
        
    if alarm_thread is not None and alarm_thread.is_alive():
        alarm_thread.join(timeout=5)  # Wait up to 5 seconds for thread to stop
        if alarm_thread.is_alive():
            print("Warning: Alarm thread did not stop gracefully")
        else:
            print("Alarm monitoring thread stopped")
    
    alarm_system = None
    alarm_thread = None
    alarm_thread_stop_event = None

def set_alarm_via_mqtt(alarm_type, state):
    """Set alarm state via MQTT communication with alarm container"""
    try:
        import paho.mqtt.client as mqtt
        
        # Create MQTT client for sending alarm commands
        mqtt_client = mqtt.Client()
        
        # Set connection timeout
        mqtt_client.connect("localhost", 1883, 60)
        
        # Wait a moment for connection to establish
        import time
        time.sleep(0.1)
        
        # Send alarm command via MQTT
        topic = f"rv/alarm/{alarm_type}/command"
        payload = "on" if state else "off"
        
        result = mqtt_client.publish(topic, payload)
        
        # Wait for message to be sent
        time.sleep(0.1)
        mqtt_client.disconnect()
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"MQTT alarm command sent: {alarm_type} -> {payload}")
            return True
        else:
            print(f"Failed to send MQTT alarm command: {result.rc}")
            return False
            
    except Exception as e:
        print(f"Error sending MQTT alarm command: {e}")
        return False

def get_alarm_status_via_mqtt():
    """Get current alarm status via MQTT from alarm container"""
    global bike_alarm_state, interior_alarm_state
    
    try:
        import paho.mqtt.client as mqtt
        import time
        
        # Store the received status
        status_received = {}
        status_complete = False
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                # Subscribe to status topics
                client.subscribe("rv/alarm/bike/status")
                client.subscribe("rv/alarm/interior/status")
            
        def on_message(client, userdata, msg):
            nonlocal status_received, status_complete
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            if topic == "rv/alarm/bike/status":
                status_received["bike"] = payload == "on"
            elif topic == "rv/alarm/interior/status":
                status_received["interior"] = payload == "on"
            
            # Check if we have both statuses
            if "bike" in status_received and "interior" in status_received:
                status_complete = True
        
        mqtt_client = mqtt.Client()
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.loop_start()
        
        # Wait for status messages (with timeout)
        timeout = 2.0  # 2 second timeout
        start_time = time.time()
        while not status_complete and (time.time() - start_time) < timeout:
            time.sleep(0.1)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        
        if status_complete:
            print(f"MQTT alarm status received: {status_received}")
            return status_received
        else:
            print("Timeout waiting for MQTT alarm status")
            # Fall back to web interface state
            return {"bike": bike_alarm_state, "interior": interior_alarm_state}
            
    except Exception as e:
        print(f"Error getting MQTT alarm status: {e}")
        # Fall back to web interface state
        return {"bike": bike_alarm_state, "interior": interior_alarm_state}

def set_alarm(alarm_type, state):
    """Set alarm state - works with direct GPIO, MQTT, or web-only mode"""
    global alarm_system, bike_alarm_state, interior_alarm_state
    
    # Always update the web interface state first
    if alarm_type == "bike":
        bike_alarm_state = state
        print(f"Web bike alarm {'activated' if state else 'deactivated'}")
    elif alarm_type == "interior":
        interior_alarm_state = state
        print(f"Web interior alarm {'activated' if state else 'deactivated'}")
    
    print(f"DEBUG: ALARM_AVAILABLE={ALARM_AVAILABLE}, alarm_system is None: {alarm_system is None}")
    
    # Try to control physical alarm - first try direct GPIO access
    if alarm_system is not None:
        try:
            if alarm_type == "bike":
                if state:
                    alarm_system.set_state(alarm.AlarmTypes.Bike, alarm.States.STARTING)
                    print("Physical bike alarm activated (direct GPIO)")
                else:
                    alarm_system.set_state(alarm.AlarmTypes.Bike, alarm.States.OFF)
                    print("Physical bike alarm deactivated (direct GPIO)")
            elif alarm_type == "interior":
                if state:
                    alarm_system.set_state(alarm.AlarmTypes.Interior, alarm.States.STARTING)
                    print("Physical interior alarm activated (direct GPIO)")
                else:
                    alarm_system.set_state(alarm.AlarmTypes.Interior, alarm.States.OFF)
                    print("Physical interior alarm deactivated (direct GPIO)")
            return
        except Exception as e:
            print(f"Error controlling physical alarm via GPIO: {e}")
    
    # If direct GPIO failed or unavailable, try MQTT communication
    # Try MQTT if alarm_system is None (running in container mode)
    print(f"DEBUG: Checking MQTT path, alarm_system is None: {alarm_system is None}")
    if alarm_system is None:  # Try MQTT if direct alarm system isn't available
        print("DEBUG: Attempting MQTT communication...")
        try:
            if set_alarm_via_mqtt(alarm_type, state):
                print(f"Physical {alarm_type} alarm {'activated' if state else 'deactivated'} (via MQTT)")
                return
            else:
                print(f"Failed to control physical alarm via MQTT")
        except Exception as e:
            print(f"Exception in MQTT communication: {e}")
    
    # Fallback to web-only mode
    print(f"Physical alarm not available - web state updated only")

class AlarmPostData(BaseModel):
    alarm: str
    state: bool

class WiFiConfigData(BaseModel):
    ssid: str
    password: str
    permanent: bool = False

class WiFiConfigData(BaseModel):
    ssid: str
    password: str
    permanent: bool = False

class WiFiConfigResponse(BaseModel):
    exit_code: int
    output: str
    success: bool

class ScheduleShutdownData(BaseModel):
    hours: int

@app.post("/api/alarmpost")
async def alarm_endpoint(data: Annotated[AlarmPostData, Body()]) -> dict:
    if debug > 0:
        print(f"Web alarm request: {data.alarm} State: {data.state}")
    
    # Use our new set_alarm function that handles both web and physical alarms
    set_alarm(data.alarm, data.state)
    
    return {"status": "ok", "alarm": data.alarm, "state": data.state}

@app.get("/api/alarmget")
async def alarms() -> dict:
    global bike_alarm_state, interior_alarm_state, alarm_system
    
    result = {
        "bike": bike_alarm_state, 
        "interior": interior_alarm_state,
        "physical_alarm_available": alarm_system is not None
    }
    
    # Add detailed physical alarm states if available
    if alarm_system is not None:
        result["physical_states"] = {
            "bike": alarm_system.BikeState.name,
            "interior": alarm_system.InteriorState.name
        }
    else:
        # Try to get status via MQTT if direct access not available
        try:
            mqtt_status = get_alarm_status_via_mqtt()
            result["mqtt_status"] = mqtt_status
            result["mqtt_available"] = True
            # Update local state with MQTT status if available
            if mqtt_status:
                result["bike"] = mqtt_status.get("bike", bike_alarm_state)
                result["interior"] = mqtt_status.get("interior", interior_alarm_state)
        except Exception as e:
            print(f"Error getting MQTT alarm status in API: {e}")
            result["mqtt_available"] = False
    
    return result

@app.post("/api/alarm/sync")
async def sync_alarm_states_manual() -> dict:
    """Manually trigger synchronization of physical alarm states with web interface"""
    if alarm_system is not None:
        sync_alarm_states()
        return {
            "status": "synced", 
            "bike": bike_alarm_state, 
            "interior": interior_alarm_state,
            "physical_states": {
                "bike": alarm_system.BikeState.name,
                "interior": alarm_system.InteriorState.name
            }
        }
    else:
        return {"status": "no_physical_alarm", "bike": bike_alarm_state, "interior": interior_alarm_state}

@app.post("/api/wifi-config")
async def wifi_config(data: Annotated[WiFiConfigData, Body()]) -> WiFiConfigResponse:
    """
    Configure WiFi settings on RP2W device using the RP5toRPZero2WControl.py script
    """
    try:
        # Path to the WiFi control script - adjust this path as needed
        script_path = "/home/tblank/code/tblank1024/WifitoHostBridge/RP5toRPZero2WControl.py"
        
        # Check if script exists
        if not os.path.exists(script_path):
            return WiFiConfigResponse(
                exit_code=1,
                output=f"WiFi control script not found at {script_path}",
                success=False
            )
        
        # Prepare command arguments
        cmd = [sys.executable, script_path, data.ssid, data.password]
        
        # Add profile name if permanent storage is requested
        if data.permanent:
            profile_name = f"RV_{data.ssid.replace(' ', '_')}"
            cmd.append(profile_name)
        
        # Execute the WiFi configuration script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        # Determine success based on exit code
        success = result.returncode == 0
        
        # Combine stdout and stderr for output
        output_lines = []
        if result.stdout:
            output_lines.append("STDOUT:")
            output_lines.append(result.stdout)
        if result.stderr:
            output_lines.append("STDERR:")
            output_lines.append(result.stderr)
        
        output = "\n".join(output_lines) if output_lines else "No output received"
        
        return WiFiConfigResponse(
            exit_code=result.returncode,
            output=output,
            success=success
        )
        
    except subprocess.TimeoutExpired:
        return WiFiConfigResponse(
            exit_code=1,
            output="WiFi configuration timed out after 30 seconds",
            success=False
        )
    except Exception as e:
        return WiFiConfigResponse(
            exit_code=1,
            output=f"Error executing WiFi configuration: {str(e)}",
            success=False
        )

# Internet Control Models and Endpoints

# USB Hub Port Control Time Delay Constants (seconds)
USB_HUB_PORT_DELAY_ALL_OFF = 0.5      # Delay after turning all ports off
USB_HUB_PORT_DELAY_BETWEEN_COMMANDS = 0.2  # Delay between individual port commands
USB_HUB_PORT_DELAY_AFTER_ON = 1.0     # Delay after turning a port on (allow device to initialize)
USB_HUB_PORT_DELAY_CONNECTION_SETTLE = 2.0  # Delay to allow connection to settle before testing

# Connection-Type-Specific Initialization Delays (seconds)
# These delays allow each internet connection type to properly initialize after power-on
CONNECTION_INIT_DELAYS = {
    'cellular': 5.0,    # Cellular modem initialization delay
    'wifi': 10.0,       # WiFi adapter initialization delay  
    'starlink': 20.0,   # Starlink terminal initialization delay
    'wired': 3.0        # Wired ethernet adapter initialization delay
}

# Connection-Type-Specific Settling Delays for Testing (seconds)  
# Additional time to wait before connectivity testing after initialization
CONNECTION_SETTLE_DELAYS = {
    'cellular': 8.0,    # Extra time for cellular network registration
    'wifi': 5.0,        # Extra time for WiFi association and DHCP
    'starlink': 15.0,   # Extra time for Starlink satellite acquisition
    'wired': 2.0        # Minimal extra time for ethernet link negotiation
}

# Port to Connection Type Mapping
# Maps USB hub port numbers to their corresponding connection types
PORT_TO_CONNECTION_TYPE = {
    1: 'cellular',
    2: 'wifi', 
    3: 'starlink',
    4: 'wired'
}

# Extended mapping for cellular-amp (same USB port, different Kasa requirements)
EXTENDED_CONNECTION_MAPPING = {
    'cellular': {'usb_port': 1, 'kasa_port': None},
    'cellular-amp': {'usb_port': 1, 'kasa_port': 1},
    'wifi': {'usb_port': 2, 'kasa_port': None},
    'starlink': {'usb_port': 3, 'kasa_port': 6},
    'wired': {'usb_port': 4, 'kasa_port': None}
}

def get_connection_init_delay(port_number):
    """Get the initialization delay for a specific port/connection type."""
    connection_type = PORT_TO_CONNECTION_TYPE.get(port_number, 'wired')
    return CONNECTION_INIT_DELAYS.get(connection_type, USB_HUB_PORT_DELAY_AFTER_ON)

def get_connection_settle_delay(connection_type):
    """Get the settling delay for a specific connection type."""
    return CONNECTION_SETTLE_DELAYS.get(connection_type, USB_HUB_PORT_DELAY_CONNECTION_SETTLE)

def detect_current_internet_connection():
    """
    Detect the current internet connection state by querying the USB hub.
    Updates the global current_internet_connection variable.
    Returns the detected connection type.
    """
    global current_internet_connection
    
    try:
        hub = get_usb_hub_controller()
        if not hub:
            print("WARNING: Could not connect to USB hub for state detection")
            current_internet_connection = "none"
            return current_internet_connection
        
        # Get the currently active port
        active_port = hub.get_current_active_port()
        
        if active_port == -1:
            print("WARNING: Could not determine hub state")
            current_internet_connection = "none"
        elif active_port == 0:
            print("INFO: No internet connection active (all ports off)")
            current_internet_connection = "none"
        elif 1 <= active_port <= 4:
            # Map port to connection type
            connection_type = PORT_TO_CONNECTION_TYPE.get(active_port, "none")
            current_internet_connection = connection_type
            print(f"INFO: Detected active internet connection: {connection_type} (port {active_port})")
        else:
            print(f"WARNING: Invalid active port detected: {active_port}")
            current_internet_connection = "none"
    
    except Exception as e:
        print(f"ERROR: Failed to detect internet connection state: {e}")
        current_internet_connection = "none"
    
    return current_internet_connection

def update_current_internet_connection(port, action):
    """Update the current internet connection state based on port control actions."""
    global current_internet_connection
    
    if port == 0 or action.lower() == 'off':
        current_internet_connection = "none"
    elif 1 <= port <= 4 and action.lower() == 'on':
        connection_type = PORT_TO_CONNECTION_TYPE.get(port, "none")
        current_internet_connection = connection_type
    
    print(f"INFO: Current internet connection updated to: {current_internet_connection}")

class InternetPowerData(BaseModel):
    port: int  # 1-4 for specific ports, 0 for all ports off
    action: str  # 'on' or 'off'
    kasaPort: int = None  # Optional Kasa power strip port
    connection_type: str = None  # Optional connection type for enhanced logic

class InternetTestData(BaseModel):
    connection_type: str  # 'cellular', 'wifi', 'starlink', 'wired'

class InternetResponse(BaseModel):
    success: bool
    message: str
    port: int = None
    connected: bool = None

# Global Kasa connection cache to prevent repeated discovery
_kasa_strip_cache = None
_kasa_cache_time = 0
_kasa_cache_duration = 300  # Cache for 5 minutes
_kasa_last_failure_time = 0
_kasa_failure_cache_duration = 15  # Reduced to 15 seconds for faster recovery when device comes back online

def get_kasa_power_strip():
    """Get Kasa Power Strip Controller instance. Returns None if not available."""
    import os
    import time
    
    global _kasa_strip_cache, _kasa_cache_time, _kasa_last_failure_time
    
    # Check if Kasa is disabled via environment variable
    if os.getenv('DISABLE_KASA', '').lower() in ('true', '1', 'yes'):
        print("INFO: Kasa power strip disabled via DISABLE_KASA environment variable")
        return None
    
    current_time = time.time()
    
    # Check if we recently had a failure and should avoid retrying
    if (_kasa_last_failure_time > 0 and 
        (current_time - _kasa_last_failure_time) < _kasa_failure_cache_duration):
        # Recent failure, don't retry yet
        return None
    
    # Check cache validity for successful connections
    if (_kasa_strip_cache is not None and 
        (current_time - _kasa_cache_time) < _kasa_cache_duration):
        # Cache is still valid, return cached instance
        return _kasa_strip_cache
    
    # Cache is invalid or doesn't exist, try to create new connection
    try:
        print("INFO: Attempting to create new Kasa power strip connection...")
        
        # Get Kasa host from constants
        kasa_host = constants.get("KASA_IP", "10.0.0.188")
        
        # Try to create and connect to Kasa power strip with balanced timeout
        kasa_strip = KasaPowerStrip(host=kasa_host, timeout=8)  # Use host from constants
        if kasa_strip.connect():
            print("INFO: Kasa power strip connected successfully")
            _kasa_strip_cache = kasa_strip
            _kasa_cache_time = current_time
            _kasa_last_failure_time = 0  # Reset failure time on success
            return kasa_strip
        else:
            print("WARNING: No Kasa power strip found or connection failed")
            print("INFO: Set DISABLE_KASA=true environment variable to disable Kasa functionality")
            # Cache the failure to avoid immediate retries
            _kasa_strip_cache = None
            _kasa_last_failure_time = current_time
            return None
    except Exception as e:
        print(f"WARNING: Kasa power strip controller not available: {e}")
        print("INFO: Set DISABLE_KASA=true environment variable to disable Kasa functionality")
        # Cache the failure to avoid immediate retries
        _kasa_strip_cache = None
        _kasa_last_failure_time = current_time
        return None

def clear_kasa_cache():
    """Clear the Kasa connection cache - useful for testing or after errors."""
    global _kasa_strip_cache, _kasa_cache_time
    _kasa_strip_cache = None
    _kasa_cache_time = 0
    print("INFO: Kasa connection cache cleared")

def get_usb_hub_controller():
    """Get USB Hub Controller instance. Returns None if not available."""
    try:
        # Import the ASCII USB hub controller from the local directory
        import sys
        import os
        
        # Use the local usbhub_ascii.py module
        local_path = os.path.dirname(os.path.abspath(__file__))
        parent_path = os.path.dirname(local_path)  # Go up one directory to RVSecurity root
        if parent_path not in sys.path:
            sys.path.append(parent_path)
        
        from usbhub_ascii import CoolGearUSBHub
        
        # Try common USB device paths
        possible_ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']
        
        for port in possible_ports:
            if os.path.exists(port):
                try:
                    hub = CoolGearUSBHub(port)
                    if hub.ser and hub.ser.is_open:
                        print(f"Successfully connected to USB hub on {port}")
                        return hub
                except Exception as e:
                    print(f"Failed to connect to USB hub on {port}: {e}")
                    continue
        
        print("No USB hub found on any of the standard ports")
        return None
        
    except ImportError as e:
        print(f"USB hub controller not available: {e}")
        return None
    except Exception as e:
        print(f"Error initializing USB hub: {e}")
        return None

def test_internet_connectivity(connection_type="generic", timeout=5):
    """Test internet connectivity using multiple methods for Docker compatibility."""
    test_results = {
        'connected': False,
        'message': 'Testing...'
    }
    
    # Method 1: Try ping command (works on host, may fail in Docker)
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), '8.8.8.8'],
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        if result.returncode == 0:
            test_results['connected'] = True
            test_results['message'] = f'Internet connectivity verified via {connection_type} (ping)'
            return test_results
        else:
            # Ping failed, but don't return yet - try other methods
            ping_error = result.stderr.strip() if result.stderr else "ping failed"
            
    except subprocess.TimeoutExpired:
        ping_error = "ping timed out"
    except Exception as e:
        ping_error = f"ping error: {str(e)}"
    
    # Method 2: Try curl as fallback (better for Docker)
    try:
        result = subprocess.run(
            ['curl', '--connect-timeout', str(timeout), '--max-time', str(timeout), 
             '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://8.8.8.8'],
            capture_output=True,
            text=True,
            timeout=timeout + 2
        )
        
        if result.returncode == 0:
            # Any HTTP response (even error codes) indicates connectivity
            test_results['connected'] = True
            test_results['message'] = f'Internet connectivity verified via {connection_type} (http)'
            return test_results
        else:
            curl_error = result.stderr.strip() if result.stderr else "http test failed"
            
    except subprocess.TimeoutExpired:
        curl_error = "http test timed out"
    except Exception as e:
        curl_error = f"http test error: {str(e)}"
    
    # Method 3: Try Python socket connection as final fallback
    try:
        import socket
        sock = socket.create_connection(("8.8.8.8", 53), timeout=timeout)
        sock.close()
        test_results['connected'] = True
        test_results['message'] = f'Internet connectivity verified via {connection_type} (socket)'
        return test_results
    except Exception as socket_error:
        socket_error_msg = str(socket_error)
    
    # All methods failed
    test_results['connected'] = False
    test_results['message'] = f'No internet connectivity detected via {connection_type} (ping: {ping_error}, http: {curl_error}, socket: {socket_error_msg})'
    
    return test_results

@app.get("/api/kasa/power/{outlet_id}")
def get_kasa_power(outlet_id: int) -> dict:  # Removed async
    """Get power consumption from a specific Kasa outlet using simple blocking calls."""
    try:
        kasa_strip = get_kasa_power_strip()
        if not kasa_strip:
            return {"success": False, "power": 0, "message": "Kasa power strip not available"}
        
        # Convert to 0-based indexing for the Kasa controller
        power_data = kasa_strip.get_power_consumption(outlet_id - 1)
        
        # Check if there was an error in the power data
        if 'error' in power_data:
            print(f"Kasa power reading error for port {outlet_id}: {power_data['error']}")
            clear_kasa_cache()  # Clear cache on error
            return {"success": False, "power": 0, "message": power_data['error']}
        
        # Extract power value in watts
        power_watts = power_data.get('power_w', 0)
        
        return {
            "success": True, 
            "power": round(power_watts, 1),
            "message": f"Power reading from Kasa port {outlet_id}: {power_watts}W"
        }
            
    except Exception as e:
        print(f"ERROR: Failed to get Kasa power for outlet {outlet_id}: {e}")
        clear_kasa_cache()  # Clear cache on error
        return {"success": False, "power": 0, "message": f"Kasa error: {str(e)}"}

@app.get("/api/internet/status")
def get_internet_status() -> dict:  # Removed async
    """Get current internet connection status."""
    global current_internet_connection
    
    try:
        # Detect current connection from USB hub
        detected_connection = detect_current_internet_connection()
        
        return {
            "current_connection": detected_connection,
            "status": "connected" if detected_connection != "none" else "disconnected",
            "message": f"Current internet connection: {detected_connection}"
        }
    except Exception as e:
        print(f"Error getting internet status: {e}")
        return {
            "current_connection": "unknown",
            "status": "error", 
            "message": f"Error detecting connection: {str(e)}"
        }

@app.post("/api/internet/power")
def internet_power_control(data: Annotated[InternetPowerData, Body()]) -> InternetResponse:  # Removed async
    """Control USB hub ports and Kasa power strip for internet connections."""
    try:
        hub = get_usb_hub_controller()
        if not hub:
            return InternetResponse(
                success=False,
                message="USB hub controller not available. Check USB hub connection.",
                port=data.port
            )
        
        # Handle mutual exclusion logic for Kasa power control
        kasa_success = True
        kasa_message = ""
        kasa_strip = None
        
        # Get Kasa strip if we need to do any Kasa operations
        try:
            kasa_strip = get_kasa_power_strip()
        except Exception as e:
            print(f"WARNING: Failed to get Kasa power strip: {e}")
        
        # Simple Kasa power control logic based on connection_type
        if kasa_strip:
            try:
                # Always manage both Kasa ports based on connection_type
                connection_type = data.connection_type or "none"
                
                # Kasa Port 1 (Cellular Amp): Only ON when cellular-amp is selected
                if connection_type == 'cellular-amp':
                    result1 = kasa_strip.turn_on_outlet(0)  # Convert to 0-based indexing (port 1 -> index 0)
                    print(f"INFO: Kasa port 1 (cellular amp) turned ON for cellular-amp")
                else:
                    result1 = kasa_strip.turn_off_outlet(0)
                    print(f"INFO: Kasa port 1 (cellular amp) turned OFF (connection: {connection_type})")
                
                # Kasa Port 6 (Starlink): Only ON when starlink is selected
                if connection_type == 'starlink':
                    result6 = kasa_strip.turn_on_outlet(5)  # Convert to 0-based indexing (port 6 -> index 5)
                    print(f"INFO: Kasa port 6 (starlink) turned ON for starlink")
                else:
                    result6 = kasa_strip.turn_off_outlet(5)
                    print(f"INFO: Kasa port 6 (starlink) turned OFF (connection: {connection_type})")
                
                # Build status message
                if connection_type == 'cellular-amp':
                    kasa_message = ", Kasa: port 1 ON, port 6 OFF"
                elif connection_type == 'starlink':
                    kasa_message = ", Kasa: port 1 OFF, port 6 ON"
                else:
                    kasa_message = ", Kasa: both ports OFF"
                    
            except Exception as e:
                print(f"WARNING: Kasa power strip operation failed: {e}")
                clear_kasa_cache()
                kasa_success = False
                kasa_message = f", Kasa control failed: {str(e)}"
        
        # USB Hub Control Logic
        if data.port == 0:  # All ports off
            result = hub.all_off()
            if result:
                time.sleep(USB_HUB_PORT_DELAY_ALL_OFF)  # Allow time for all ports to turn off
                update_current_internet_connection(0, "off")  # Update state
                
                success_msg = "All USB ports powered off"
                if not kasa_success:
                    success_msg += kasa_message
                
                return InternetResponse(
                    success=True,
                    message=success_msg,
                    port=0
                )
            else:
                return InternetResponse(
                    success=False,
                    message="Failed to power off all USB ports" + kasa_message,
                    port=0
                )
        
        elif 1 <= data.port <= 4:  # Specific port control
            # Use the connection_type from the request data, or fallback to port mapping
            connection_type = data.connection_type or PORT_TO_CONNECTION_TYPE.get(data.port, 'wired')
            init_delay = get_connection_init_delay(data.port)
            
            if data.action.lower() == 'on':
                # Use atomic single-port control to avoid multi-port transitions
                print(f"Setting ONLY port {data.port} ON ({connection_type}) - all others OFF")
                result = hub.set_single_port_on(data.port)
                if result:
                    print(f"Applying {connection_type} initialization delay: {init_delay} seconds")
                    time.sleep(init_delay)  # Use connection-specific initialization delay
                    
                    # Special handling for cellular modem (port 1)
                    if data.port == 1 and connection_type == 'cellular':
                        print("Performing cellular modem setup sequence...")
                        try:
                            modem_success, modem_message = usb_modem_manager.prepare_cellular_modem()
                            if modem_success:
                                action_msg = f"powered on ({connection_type}) - modem configured"
                                print(f"Cellular modem setup successful: {modem_message}")
                            else:
                                action_msg = f"powered on ({connection_type}) - modem setup failed: {modem_message}"
                                print(f"Cellular modem setup failed: {modem_message}")
                        except Exception as e:
                            action_msg = f"powered on ({connection_type}) - modem setup error: {str(e)}"
                            print(f"Cellular modem setup error: {e}")
                    else:
                        action_msg = f"powered on ({connection_type})"
                else:
                    action_msg = f"failed to power on ({connection_type})"
            else:
                result = hub.port_off(data.port)
                if result:
                    time.sleep(USB_HUB_PORT_DELAY_BETWEEN_COMMANDS)  # Brief pause
                action_msg = f"powered off ({connection_type})"
            
            if result:
                update_current_internet_connection(data.port, data.action)  # Update state
                
                success_msg = f"USB port {data.port} {action_msg} successfully"
                if kasa_success and data.kasaPort:
                    success_msg += kasa_message
                elif not kasa_success and data.kasaPort:
                    success_msg += kasa_message
                
                return InternetResponse(
                    success=True,
                    message=success_msg,
                    port=data.port
                )
            else:
                return InternetResponse(
                    success=False,
                    message=f"Failed to {data.action} USB port {data.port}" + kasa_message,
                    port=data.port
                )
        
        else:
            return InternetResponse(
                success=False,
                message=f"Invalid port number: {data.port}. Use 1-4 for specific ports, 0 for all off.",
                port=data.port
            )
    
    except Exception as e:
        return InternetResponse(
            success=False,
            message=f"USB hub control error: {str(e)}",
            port=data.port
        )

@app.post("/api/internet/cellular-test")
def test_cellular_modem_setup() -> InternetResponse:
    """Test cellular modem setup and configuration."""
    try:
        print("Starting manual cellular modem test...")
        
        # Test the USB modem manager
        success, message = usb_modem_manager.prepare_cellular_modem()
        
        return InternetResponse(
            success=success,
            message=f"Cellular modem test: {message}",
            connected=success
        )
        
    except Exception as e:
        return InternetResponse(
            success=False,
            message=f"Cellular modem test failed: {str(e)}",
            connected=False
        )

@app.post("/api/internet/test")
def internet_connectivity_test(data: Annotated[InternetTestData, Body()]) -> InternetResponse:  # Removed async
    """Test internet connectivity for the specified connection type."""
    try:
        # Use connection-specific settling delay before testing
        settle_delay = get_connection_settle_delay(data.connection_type)
        print(f"Applying {data.connection_type} connection settle delay: {settle_delay} seconds")
        time.sleep(settle_delay)
        
        # Test internet connectivity with shorter timeout for the simplified ping test
        timeout = 5  # Fast ping test timeout
        test_results = test_internet_connectivity(data.connection_type, timeout=timeout)
        
        return InternetResponse(
            success=True,
            message=test_results['message'],
            connected=test_results['connected']
        )
    
    except Exception as e:
        return InternetResponse(
            success=False,
            message=f"Connectivity test failed: {str(e)}",
            connected=False
        )

class DataResponse(BaseModel):
    var1: str
    var2: str
    var3: str
    var4: str
    var5: str
    var6: str
    var7: str
    var8: str
    var9: str
    var10: str
    var11: str
    var12: str
    var13: str
    var14: str
    var15: str
    var16: str
    var17: str
    var18: str
    var19: str
    var20: str
    battery_percent: float


# This is the POWER page function that is called by the front end client
@app.get("/data/power")
def data_power()-> DataResponse:  # Removed async
    debug = 0  # Define debug variable

    (Charger_AC_power, Charger_AC_voltage, Invert_AC_power, DC_Charger_power, DC_Charger_volts, Invert_DC_power, Invert_status_num)= InvertCalcs()
    (ShorePower, GenPower)= ATS_Calcs()
    (SolarPower) = SolcarCalcs()
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs(debug)
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, Invert_DC_power, SolarPower)

    (BatteryFlow, InvertPwrFlow, ShorePwrFlow, GeneratorPwrFlow, SolarPwrFlow, AltPwrFlow, Invert_status_str) = \
        GenAllFlows(Invert_status_num, Batt_Power, SolarPower, ShorePower, GenPower, AlternatorPower)

    #Calc AC and DC Loads since not measured
    (AC_HeatPump_Load, DC_Load) = LoadCalcs(Invert_status_num, Charger_AC_power, DC_Charger_power, ShorePower, GenPower, Batt_Power, SolarPower, AlternatorPower, Invert_DC_power)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    return DataResponse(
        var1 =str(max(ShorePower, GenPower)) + ' Watts',      #shore or gen power (watts)
        var2 =ShorePwrFlow,                                             #shorepower Flow
        var3 =str('%.0f' % Charger_AC_voltage) + " Volts AC",
        var4 =str('%.0f' % AC_HeatPump_Load) + ' Watts',  
        var5 =str(SolarPower) + ' Watts',
        var6 =SolarPwrFlow,                                             #solar power Flow
        var7 =str('%.1f' % Batt_Voltage) + " Volts DC",
        var8 =str('%.0f' % DC_Load) + ' Watts',
        var9 = str('%.0f' % AlternatorPower) + " Watts",                                #Alternator power
        var10=InvertPwrFlow,                                            #flow annimation   
        var11=str('%.0f' % Charger_AC_power) + " Watts", 
        var12= str('%.0f' % max(Invert_AC_power, .8 * (Invert_DC_power)) + " Watts"),      #note: .8 is efficiency estimate of inverter
        var13=RedMsg, 
        var14=AltPwrFlow,                                               #Alternator power Flow
        #battery variables begin
        var15= Batt_Hours_Remaining_str,
        var16= 'Status: ' + Batt_status_str,
        var17= GeneratorPwrFlow,
        var18= BatteryFlow,                        #Battery power Flow
        var19= str('%.0f' % Batt_Power) + " Watts",
        battery_percent= Batt_Charge,
        #battery variables end 
        var20=Time_Str,
        
    )

# This is the HOME page function that is called by the front end client
@app.get("/data/home")
def data_home()-> DataResponse:  # Removed async
    debug = 0  # Define debug variable
    
    (Charger_AC_power, Charger_AC_voltage, Invert_AC_power, DC_Charger_power, DC_Charger_volts, Invert_DC_power, Invert_status_num)= InvertCalcs()
    (ShorePower, GenPower)= ATS_Calcs()
    (SolarPower) = SolcarCalcs()
    (Batt_Power, Batt_Voltage, Batt_Charge, Batt_Hours_Remaining_str, Batt_status_str) = BatteryCalcs(debug)
    (AlternatorPower) = AlternatorCalcs(Batt_Power, Invert_status_num, Invert_DC_power, SolarPower)

    #Calc AC and DC Loads since not measured
    (AC_HeatPump_Load, DC_Load) = LoadCalcs(Invert_status_num, Charger_AC_power, DC_Charger_power, ShorePower, GenPower, Batt_Power, SolarPower, AlternatorPower, Invert_DC_power)
    (RedMsg, YellowMsg, Time_Str) = HouseKeeping()

    # Tank level calculations with error handling for missing data
    try:
        Tank_Fresh = round(rvglue.rvglue.AliasData["_var29Tank_Level"]/rvglue.rvglue.AliasData["_var30Tank_Resolution"] * 100 )  
    except (KeyError, ZeroDivisionError):
        Tank_Fresh = 50  # Default value when no data available
        
    try:
        Tank_Black = round(rvglue.rvglue.AliasData["_var32Tank_Level"]/rvglue.rvglue.AliasData["_var33Tank_Resolution"] * 100)
    except (KeyError, ZeroDivisionError):
        Tank_Black = 25  # Default value when no data available
        
    try:
        Tank_Gray = round(rvglue.rvglue.AliasData["_var35Tank_Level"]/rvglue.rvglue.AliasData["_var36Tank_Resolution"] * 100)   
    except (KeyError, ZeroDivisionError):
        Tank_Gray = 30  # Default value when no data available
        
    try:
        Tank_Propane = round(rvglue.rvglue.AliasData["_var38Tank_Level"]/rvglue.rvglue.AliasData["_var39Tank_Resolution"] * 100)  
    except (KeyError, ZeroDivisionError):
        Tank_Propane = 75  # Default value when no data available  

    if debug > 0:
        print('invert power= ', round(Invert_AC_power), round(Invert_DC_power*.8))

    return DataResponse(
        var1 = 'Outside 60? psi',   # LR outside
        var2 = 'Inside 60? psi',    # LR inside
        var3 = 'Inside 60? psi',   # RR inside
        var4 = 'Outside 60? psi',    # RR outside
        var5 = str(SolarPower) + ' Watts',
        var6 = 'not used',                                            
        var7 = str('%.1f' % Batt_Voltage) + " Volts DC",
        var8 = str('%.0f' % DC_Load) + ' Watts',
        var9 = '60? psi',    # LF
        var10= '60? psi',    # RF
        var11= 'not used',  
        var12= str('%.0f' % max(Invert_AC_power, .8 * (Invert_DC_power)) + " Watts"),      #note: .8 is efficiency estimate of inverter
        var13= str(Tank_Gray),   # Send as string, client will convert to number
        var14= str(Tank_Black),  # Send as string, client will convert to number
        var15= Batt_Hours_Remaining_str,
        var16= 'Status: ' + Batt_status_str,
        var17= str(Tank_Fresh),  # Send as string, client will convert to number
        var18= str(Tank_Propane), # Send as string, client will convert to number
        var19= str('%.0f' % Batt_Power) + " Watts",
        battery_percent= Batt_Charge,
        var20= Time_Str,
        
    )

# Debug API endpoints
@app.get("/api/debug/usb/status")
def get_usb_debug_status() -> dict:
    """Get current status of all USB ports for debug interface."""
    try:
        hub = get_usb_hub_controller()
        if not hub:
            return {
                "success": False,
                "message": "USB hub controller not available",
                "ports": {}
            }
        
        # Get status of all USB ports
        ports = {}
        for port_num in range(1, 5):  # USB ports 1-4
            try:
                # Get current active port and determine if this specific port is on
                active_port = hub.get_current_active_port()
                is_on = (active_port == port_num)
                connection_type = PORT_TO_CONNECTION_TYPE.get(port_num, 'unknown')
                ports[port_num] = {
                    "enabled": is_on,
                    "connection_type": connection_type,
                    "name": f"USB Port {port_num} ({connection_type.title()})"
                }
            except Exception as e:
                ports[port_num] = {
                    "enabled": False,
                    "connection_type": PORT_TO_CONNECTION_TYPE.get(port_num, 'unknown'),
                    "name": f"USB Port {port_num} (Error)",
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": "USB ports status retrieved",
            "ports": ports
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting USB status: {str(e)}",
            "ports": {}
        }

@app.post("/api/debug/usb/{port_num}")
def control_usb_port_debug(port_num: int, data: Annotated[dict, Body()]) -> dict:
    """Control individual USB port for debug interface."""
    try:
        if port_num < 1 or port_num > 4:
            return {
                "success": False,
                "message": f"Invalid port number: {port_num}. Must be 1-4."
            }
        
        action = data.get('action', '').lower()
        if action not in ['on', 'off']:
            return {
                "success": False,
                "message": f"Invalid action: {action}. Must be 'on' or 'off'."
            }
        
        hub = get_usb_hub_controller()
        if not hub:
            return {
                "success": False,
                "message": "USB hub controller not available"
            }
        
        # Control the specific port
        if action == 'on':
            result = hub.port_on(port_num)
        else:
            result = hub.port_off(port_num)
        
        if result:
            connection_type = PORT_TO_CONNECTION_TYPE.get(port_num, 'unknown')
            return {
                "success": True,
                "message": f"USB port {port_num} ({connection_type}) turned {action}",
                "port": port_num,
                "action": action
            }
        else:
            return {
                "success": False,
                "message": f"Failed to turn {action} USB port {port_num}",
                "port": port_num,
                "action": action
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error controlling USB port {port_num}: {str(e)}",
            "port": port_num
        }

@app.get("/api/debug/kasa/status")
def get_kasa_debug_status() -> dict:
    """Get current status and power consumption of all Kasa outlets for debug interface."""
    import time
    global _kasa_last_failure_time
    
    # Fast fail if we recently had a connection failure
    current_time = time.time()
    if (_kasa_last_failure_time > 0 and 
        (current_time - _kasa_last_failure_time) < _kasa_failure_cache_duration):
        print("INFO: Debug page - using cached failure, returning mock data immediately")
        return {
            "success": True,
            "message": "Kasa device recently failed - showing cached offline status",
            "outlets": {
                1: {"enabled": False, "power_watts": 0, "name": "Kasa Outlet 1 (Cellular Amp) [OFFLINE]", "mock": True, "status": "offline"},
                2: {"enabled": True, "power_watts": 0.1, "name": "Kasa Outlet 2 (TV) [OFFLINE]", "mock": True, "status": "offline"},
                3: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 3 (Soundbar) [OFFLINE]", "mock": True, "status": "offline"},
                4: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 4 (Synology) [OFFLINE]", "mock": True, "status": "offline"},
                5: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 5 [OFFLINE]", "mock": True, "status": "offline"},
                6: {"enabled": False, "power_watts": 0.0, "name": "Kasa Outlet 6 (Starlink) [OFFLINE]", "mock": True, "status": "offline"}
            }
        }
    
    try:
        kasa_strip = get_kasa_power_strip()
        if not kasa_strip:
            # Return mock data when Kasa is not available
            return {
                "success": True,
                "message": "Kasa power strip not available - showing mock data for testing",
                "outlets": {
                    1: {"enabled": False, "power_watts": 0, "name": "Kasa Outlet 1 (Cellular Amp) [OFFLINE]", "mock": True, "status": "offline"},
                    2: {"enabled": True, "power_watts": 0.1, "name": "Kasa Outlet 2 (TV) [OFFLINE]", "mock": True, "status": "offline"},
                    3: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 3 (Soundbar) [OFFLINE]", "mock": True, "status": "offline"},
                    4: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 4 (Synology) [OFFLINE]", "mock": True, "status": "offline"},
                    5: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 5 [OFFLINE]", "mock": True, "status": "offline"},
                    6: {"enabled": False, "power_watts": 0.0, "name": "Kasa Outlet 6 (Starlink) [OFFLINE]", "mock": True, "status": "offline"}
                }
            }
        
        # Test connection first before trying to get individual outlets
        try:
            # Try a simple connection test
            if not kasa_strip.test_connectivity():
                raise KasaPowerStripError("Connection test failed")
        except Exception as e:
            # Connection failed, return mock data with error info
            error_msg = str(e)
            # Remove technical details for user-friendly message
            if "Kasa command failed:" in error_msg:
                error_msg = "Device connection failed"
            elif "Kasa communication error" in error_msg:
                error_msg = "Device temporarily unavailable"
            
            return {
                "success": True,
                "message": f"Kasa device unavailable ({error_msg}) - showing mock data",
                "outlets": {
                    1: {"enabled": False, "power_watts": 0, "name": "Kasa Outlet 1 (Cellular Amp) [ERROR]", "mock": True, "status": "error"},
                    2: {"enabled": True, "power_watts": 0.1, "name": "Kasa Outlet 2 (TV) [ERROR]", "mock": True, "status": "error"},
                    3: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 3 (Soundbar) [ERROR]", "mock": True, "status": "error"},
                    4: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 4 (Synology) [ERROR]", "mock": True, "status": "error"},
                    5: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 5 [ERROR]", "mock": True, "status": "error"},
                    6: {"enabled": False, "power_watts": 0.0, "name": "Kasa Outlet 6 (Starlink) [ERROR]", "mock": True, "status": "error"}
                }
            }
        
        # Connection successful, get real outlet data
        outlets = {}
        for outlet_id in range(1, 7):  # Kasa outlets 1-6
            try:
                # Get outlet status (this gives us the on/off state)
                status_data = kasa_strip.get_outlet_status(outlet_id - 1)  # Convert to 0-based
                
                if 'error' in status_data:
                    outlets[outlet_id] = {
                        "enabled": False,
                        "power_watts": 0,
                        "name": f"Kasa Outlet {outlet_id} [COMM ERROR]",
                        "error": "Communication error",
                        "status": "comm_error"
                    }
                else:
                    is_on = status_data.get('is_on', False)
                    
                    # Also get power consumption
                    try:
                        power_data = kasa_strip.get_power_consumption(outlet_id - 1)
                        power_watts = power_data.get('power_w', 0) if 'error' not in power_data else 0
                    except:
                        power_watts = 0
                    
                    # Get outlet name/alias if available
                    outlet_names = {
                        1: "Kasa Outlet 1 (Cellular Amp)",
                        2: "Kasa Outlet 2 (TV)", 
                        3: "Kasa Outlet 3 (Soundbar)",
                        4: "Kasa Outlet 4 (Synology)",
                        5: "Kasa Outlet 5",
                        6: "Kasa Outlet 6 (Starlink)"
                    }
                    
                    outlets[outlet_id] = {
                        "enabled": is_on,
                        "power_watts": round(power_watts, 1),
                        "name": outlet_names.get(outlet_id, f"Kasa Outlet {outlet_id}"),
                        "status": "online"
                    }
            except Exception as e:
                outlets[outlet_id] = {
                    "enabled": False,
                    "power_watts": 0,
                    "name": f"Kasa Outlet {outlet_id} [ERROR]",
                    "error": "Individual outlet error",
                    "status": "error"
                }
        
        return {
            "success": True,
            "message": "Kasa outlets status retrieved successfully",
            "outlets": outlets
        }
    except Exception as e:
        # Complete failure, return mock data
        error_msg = str(e)[:100]  # Limit error message length
        return {
            "success": True,
            "message": f"Kasa system error ({error_msg}) - showing mock data",
            "outlets": {
                1: {"enabled": False, "power_watts": 0, "name": "Kasa Outlet 1 (Cellular Amp) [SYSTEM ERROR]", "mock": True, "status": "system_error"},
                2: {"enabled": True, "power_watts": 0.1, "name": "Kasa Outlet 2 (TV) [SYSTEM ERROR]", "mock": True, "status": "system_error"},
                3: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 3 (Soundbar) [SYSTEM ERROR]", "mock": True, "status": "system_error"},
                4: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 4 (Synology) [SYSTEM ERROR]", "mock": True, "status": "system_error"},
                5: {"enabled": True, "power_watts": 0.0, "name": "Kasa Outlet 5 [SYSTEM ERROR]", "mock": True, "status": "system_error"},
                6: {"enabled": False, "power_watts": 0.0, "name": "Kasa Outlet 6 (Starlink) [SYSTEM ERROR]", "mock": True, "status": "system_error"}
            }
        }

@app.post("/api/debug/kasa/clear-cache")
def clear_kasa_cache_debug() -> dict:
    """Clear Kasa connection cache to force reconnection attempt."""
    clear_kasa_cache()
    return {"success": True, "message": "Kasa connection cache cleared"}

@app.post("/api/debug/kasa/{outlet_id}")
def control_kasa_outlet_debug(outlet_id: int, data: Annotated[dict, Body()]) -> dict:
    """Control individual Kasa outlet for debug interface."""
    try:
        if outlet_id < 1 or outlet_id > 6:
            return {
                "success": False,
                "message": f"Invalid outlet ID: {outlet_id}. Must be 1-6."
            }
        
        action = data.get('action', '').lower()
        if action not in ['on', 'off']:
            return {
                "success": False,
                "message": f"Invalid action: {action}. Must be 'on' or 'off'."
            }
        
        kasa_strip = get_kasa_power_strip()
        if not kasa_strip:
            # Return mock response when Kasa is not available
            mock_power = 0.1 if action == 'on' else 0.0
            return {
                "success": True,
                "message": f"Kasa outlet {outlet_id} turned {action} (mock mode)",
                "outlet": outlet_id,
                "action": action,
                "power_watts": mock_power,
                "mock": True
            }
        
        # Control the specific outlet (convert to 0-based indexing)
        if action == 'on':
            result = kasa_strip.turn_on_outlet(outlet_id - 1)
        else:
            result = kasa_strip.turn_off_outlet(outlet_id - 1)
        
        # Get power consumption after the action (with a small delay)
        time.sleep(0.5)
        try:
            power_data = kasa_strip.get_power_consumption(outlet_id - 1)
            power_watts = power_data.get('power_w', 0) if 'error' not in power_data else 0
        except:
            power_watts = 0
        
        # Clear cache to ensure next status request gets fresh data
        clear_kasa_cache()
        
        return {
            "success": True,
            "message": f"Kasa outlet {outlet_id} turned {action}",
            "outlet": outlet_id,
            "action": action,
            "power_watts": round(power_watts, 1)
        }
    except Exception as e:
        # Return mock response on error
        mock_power = 0.1 if action == 'on' else 0.0
        return {
            "success": True,
            "message": f"Kasa outlet {outlet_id} turned {action} (mock mode - error: {str(e)})",
            "outlet": outlet_id,
            "action": action,
            "power_watts": mock_power,
            "mock": True,
            "error": str(e)
        }

# Synology scheduled shutdown endpoints (must come before generic handler)
@app.get("/api/debug/synology/scheduled-time")
async def get_scheduled_shutdown():
    """Get the scheduled shutdown timestamp"""
    global scheduled_shutdown_timestamp
    return {
        "success": True,
        "scheduled_time": scheduled_shutdown_timestamp
    }

@app.post("/api/debug/synology/schedule-shutdown")
async def schedule_shutdown(data: Annotated[ScheduleShutdownData, Body()]):
    """Schedule a shutdown for X hours from now"""
    global scheduled_shutdown_timestamp
    
    if data.hours > 0:
        delay_seconds = data.hours * 3600
        scheduled_shutdown_timestamp = time.time() + delay_seconds
        
        # Start the actual timer that will execute the shutdown
        schedule_shutdown_timer(delay_seconds)
        
        return {
            "success": True,
            "scheduled_time": scheduled_shutdown_timestamp,
            "message": f"Server scheduled to turn off in {data.hours} hours"
        }
    else:
        # Cancel scheduled shutdown
        cancel_shutdown_timer()
        scheduled_shutdown_timestamp = None
        return {
            "success": True,
            "scheduled_time": None,
            "message": "Scheduled shutdown cancelled"
        }

@app.delete("/api/debug/synology/scheduled-time")
async def cancel_scheduled_shutdown():
    """Cancel any scheduled shutdown"""
    global scheduled_shutdown_timestamp
    
    # Cancel the timer
    cancel_shutdown_timer()
    scheduled_shutdown_timestamp = None
    
    return {
        "success": True,
        "scheduled_time": None,
        "message": "Scheduled shutdown cancelled"
    }

# Synology NAS debug endpoints
@app.post("/api/debug/synology/{action}")
async def debug_synology_control(action: str):
    """Control Synology NAS (status, power-on, power-off)"""
    try:
        import subprocess
        import os
        
        if action not in ['status', 'power-on', 'power-off']:
            return {
                "success": False,
                "message": f"Invalid action: {action}. Valid actions: status, power-on, power-off"
            }
        
        # Get the current directory (server directory)
        server_dir = os.path.dirname(os.path.abspath(__file__))
        password_file = os.path.join(server_dir, 'synology-password.json')
        
        # Use the command line interface for faster response
        cmd = ['python', 'synology_nas_controller.py', f'--{action}', '--config', password_file]
        
        # Add --force flag for power-off to skip confirmation prompt
        if action == 'power-off':
            cmd.append('--force')
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=server_dir)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            
            # If this is a power-off command, cancel any scheduled shutdown timer
            if action == 'power-off':
                cancel_shutdown_timer()
                global scheduled_shutdown_timestamp
                scheduled_shutdown_timestamp = None
            
            # For status command, try to parse additional info
            if action == 'status' and 'NAS Status:' in output:
                # Extract status information from output
                lines = output.split('\n')
                status_info = {}
                for line in lines:
                    if ':' in line and any(key in line for key in ['Online', 'IP', 'MAC', 'Ethernet', 'Model']):
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip().lower().replace(' ', '_')
                            value = parts[1].strip()
                            # Handle boolean values
                            if value.lower() in ['yes', 'true']:
                                value = True
                            elif value.lower() in ['no', 'false']:
                                value = False
                            status_info[key] = value
                
                return {
                    "success": True,
                    "message": output,
                    "status": status_info
                }
            else:
                return {
                    "success": True,
                    "message": output
                }
        else:
            error_msg = result.stderr.strip() if result.stderr else "Command failed"
            # Include both stdout and stderr for better debugging
            full_error = f"STDERR: {result.stderr}\nSTDOUT: {result.stdout}" if result.stderr and result.stdout else error_msg
            return {
                "success": False,
                "message": f"Synology {action} failed: {full_error}"
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": f"Synology {action} command timed out (15s)"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error controlling Synology NAS: {str(e)}"
        }



@app.get("/status")
async def status() -> dict:
    return {"hello": "world and more"}

import os
if os.path.exists("build") and os.path.isdir("build"):
    static_files = StaticFiles(directory="build")
    app.mount("/", static_files, name="ui")


if __name__ == "__main__":
    
    # Register cleanup functions
    atexit.register(cleanup_alarm_system)
    
    def signal_handler(signum, frame):
        print(f"Received signal {signum}, cleaning up...")
        cleanup_alarm_system()
        sys.exit(0)
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    #kick off threads here  
    # MQTTClient("pub","localhost", 1883, "dgn_variables.json",'_var', 'RVC', debug) 
    debug = 0
    client = MQTTClient("sub","localhost", 1883, '_var', 'RVC', debug)
    t1 = threading.Thread(target=client.run_mqtt_infinite)
    #t1 = threading.Thread(target=MQTTClient.MQTTClient().printhello)
    t1.start()

    # Initialize internet connection state from USB hub
    print("Detecting current internet connection state...")
    detected_connection = detect_current_internet_connection()
    print(f"Server startup: Current internet connection is '{detected_connection}'")

    # Initialize alarm system
    print("Initializing alarm system...")
    initialize_alarm_system()

    # "0.0.0.0" => accept requests from any IP addr
    # default port is 8000.  Dockerfile sets port = 80 using environment variable

    
   
    print(constants["IPADDR"], constants["PORT"])
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=int(constants["PORT"]), log_level="warning")
    except KeyboardInterrupt:
        print("Server interrupted by user")
    finally:
        cleanup_alarm_system()
