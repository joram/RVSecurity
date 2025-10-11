#!/usr/bin/env python3
"""
Synology NAS Controller for DS620slim
Provides functionality to wake up and shutdown a Synology NAS using Wake-on-LAN and API calls.
"""

import socket
import struct
import time
import requests
import logging
import os
import json
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SynologyNASController:
    """
    Controller class for Synology DS620slim NAS.
    Supports Wake-on-LAN for power on and API calls for shutdown.
    Configuration loaded from environment variables and config file.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the Synology NAS controller.
        
        Args:
            config_file (str, optional): Path to config file. If None, uses default locations.
        
        Configuration priority (highest to lowest):
        1. Environment variables
        2. Config file
        3. Default values
        
        Environment variables:
        - SYNOLOGY_IP: IP address of the NAS
        - SYNOLOGY_MAC: MAC address for Wake-on-LAN
        - SYNOLOGY_USER: Admin username
        - SYNOLOGY_PASSWORD: Admin password
        - SYNOLOGY_PORT: DSM port (default: 5000)
        - SYNOLOGY_ETHERNET_PORT: Ethernet port connected to NAS (default: eth0)
        """
        # Load configuration
        config = self._load_config(config_file)
        
        self.ip_address = config['ip_address']
        self.mac_address = config['mac_address'].replace(':', '').replace('-', '').upper()
        self.admin_user = config['admin_user']
        self.admin_password = config['admin_password']
        self.port = config['port']
        self.ethernet_port = config['ethernet_port']
        self.base_url = f"http://{self.ip_address}:{self.port}"
        self.session_id: Optional[str] = None
        
        # Validate MAC address format
        if len(self.mac_address) != 12:
            raise ValueError("MAC address must be 12 hex characters")
    
    def _load_config(self, config_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from environment variables and config file.
        
        Args:
            config_file (str, optional): Path to config file
            
        Returns:
            dict: Configuration dictionary
            
        Raises:
            ValueError: If required configuration is missing
        """
        # Default configuration
        config = {
            'ip_address': None,
            'mac_address': None,
            'admin_user': None,
            'admin_password': None,
            'port': 5000,
            'ethernet_port': 'eth0'
        }
        
        # Try to load from config file
        config_data = self._load_config_file(config_file)
        if config_data:
            config.update(config_data)
        
        # Override with environment variables (highest priority)
        env_mapping = {
            'SYNOLOGY_IP': 'ip_address',
            'SYNOLOGY_MAC': 'mac_address',
            'SYNOLOGY_USER': 'admin_user',
            'SYNOLOGY_PASSWORD': 'admin_password',
            'SYNOLOGY_PORT': 'port',
            'SYNOLOGY_ETHERNET_PORT': 'ethernet_port'
        }
        
        for env_var, config_key in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value:
                if config_key == 'port':
                    config[config_key] = int(env_value)
                else:
                    config[config_key] = env_value
        
        # Validate required configuration
        required_fields = ['ip_address', 'mac_address', 'admin_user', 'admin_password']
        missing_fields = [field for field in required_fields if not config[field]]
        
        if missing_fields:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing_fields)}. "
                f"Set environment variables or provide config file."
            )
        
        return config
    
    def _load_config_file(self, config_file: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Load configuration from JSON file.
        
        Args:
            config_file (str, optional): Path to config file
            
        Returns:
            dict or None: Configuration data or None if file not found
        """
        # Default config file locations (in order of preference)
        default_locations = [
            'synology_nas_config.json',
            os.path.expanduser('~/.config/rvSecurity/synology_nas_config.json'),
            '/etc/rvSecurity/synology_nas_config.json'
        ]
        
        config_paths = [config_file] if config_file else default_locations
        
        for config_path in config_paths:
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config_data = json.load(f)
                    logger.info(f"Loaded configuration from {config_path}")
                    return config_data
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return None
    
    @classmethod
    def create_config_template(cls, config_file: str = 'synology_nas_config.json') -> None:
        """
        Create a template configuration file.
        
        Args:
            config_file (str): Path for the config file template
        """
        template = {
            "ip_address": "192.168.1.100",
            "mac_address": "00:11:32:44:55:66",
            "admin_user": "admin",
            "admin_password": "your_secure_password_here",
            "port": 5000,
            "ethernet_port": "eth0",
            "_comment": "This file contains sensitive information. Do not commit to version control!"
        }
        
        try:
            with open(config_file, 'w') as f:
                json.dump(template, f, indent=2)
            
            # Set restrictive permissions (Unix-like systems only)
            try:
                os.chmod(config_file, 0o600)  # Read/write for owner only
            except (AttributeError, OSError):
                pass  # Not Unix-like or permission change failed
            
            logger.info(f"Created config template at {config_file}")
            print(f"Config template created at {config_file}")
            print("Please edit this file with your actual NAS details.")
            print("DO NOT commit this file to version control!")
            
        except IOError as e:
            logger.error(f"Failed to create config template: {e}")
            raise
    
    def _send_magic_packet(self, mac_address: str, broadcast_ip: str = '255.255.255.255', port: int = 9) -> bool:
        """
        Send a Wake-on-LAN magic packet.
        
        Args:
            mac_address (str): MAC address without separators (12 hex chars)
            broadcast_ip (str): Broadcast IP address
            port (int): UDP port for WoL packet
            
        Returns:
            bool: True if packet was sent successfully
        """
        try:
            # Create magic packet: 6 bytes of 0xFF followed by 16 repetitions of MAC address
            mac_bytes = bytes.fromhex(mac_address)
            magic_packet = b'\xFF' * 6 + mac_bytes * 16
            
            # Send the packet
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.sendto(magic_packet, (broadcast_ip, port))
            
            logger.info(f"Wake-on-LAN packet sent to {mac_address}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send Wake-on-LAN packet: {e}")
            return False
    
    def _authenticate(self) -> bool:
        """
        Authenticate with the Synology DSM API.
        
        Returns:
            bool: True if authentication successful
        """
        try:
            auth_url = f"{self.base_url}/webapi/auth.cgi"
            params = {
                'api': 'SYNO.API.Auth',
                'version': '3',
                'method': 'login',
                'account': self.admin_user,
                'passwd': self.admin_password,
                'session': 'SurveillanceStation',
                'format': 'cookie'
            }
            
            response = requests.get(auth_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                self.session_id = data.get('data', {}).get('sid')
                logger.info("Successfully authenticated with Synology NAS")
                return True
            else:
                logger.error(f"Authentication failed: {data.get('error', {})}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _logout(self) -> None:
        """Logout from the Synology DSM API."""
        if not self.session_id:
            return
            
        try:
            logout_url = f"{self.base_url}/webapi/auth.cgi"
            params = {
                'api': 'SYNO.API.Auth',
                'version': '3',
                'method': 'logout',
                'session': 'SurveillanceStation'
            }
            
            requests.get(logout_url, params=params, timeout=5)
            self.session_id = None
            logger.info("Logged out from Synology NAS")
            
        except Exception as e:
            logger.warning(f"Logout error (non-critical): {e}")
    
    def _is_ethernet_port_active(self) -> bool:
        """
        Check if the specified ethernet port is active and has a link.
        
        Returns:
            bool: True if ethernet port is active and has link
        """
        try:
            # Check if interface exists and is up
            with open(f'/sys/class/net/{self.ethernet_port}/operstate', 'r') as f:
                state = f.read().strip()
            
            if state != 'up':
                logger.error(f"Ethernet port {self.ethernet_port} is not up (state: {state})")
                return False
            
            # Check if carrier is detected (cable connected)
            try:
                with open(f'/sys/class/net/{self.ethernet_port}/carrier', 'r') as f:
                    carrier = f.read().strip()
                
                if carrier != '1':
                    logger.error(f"Ethernet port {self.ethernet_port} has no carrier (cable disconnected)")
                    return False
            except IOError:
                # Some interfaces don't support carrier detection
                logger.warning(f"Cannot check carrier status for {self.ethernet_port}")
            
            logger.info(f"Ethernet port {self.ethernet_port} is active and ready")
            return True
            
        except IOError as e:
            logger.error(f"Failed to check ethernet port {self.ethernet_port}: {e}")
            return False
    
    def is_online(self) -> bool:
        """
        Check if the NAS is online by attempting to connect to the DSM interface.
        
        Returns:
            bool: True if NAS is online and responding
        """
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def power_on(self) -> bool:
        """
        Power on the NAS using Wake-on-LAN.
        First verifies that the ethernet port is active before sending WoL packet.
        
        Returns:
            bool: True if WoL packet was sent successfully
        """
        logger.info(f"Attempting to power on NAS at {self.ip_address}")
        
        if self.is_online():
            logger.info("NAS is already online")
            return True
        
        # Check if ethernet port is active before attempting WoL
        if not self._is_ethernet_port_active():
            logger.error(f"Cannot send Wake-on-LAN: ethernet port {self.ethernet_port} is not active")
            return False
        
        # Use subnet broadcast with port 7 (approach 4 from troubleshooting)
        # This was found to work better than global broadcast with port 9
        subnet_broadcast = f"{self.ip_address.rsplit('.', 1)[0]}.255"
        return self._send_magic_packet(self.mac_address, broadcast_ip=subnet_broadcast, port=7)
    
    def power_off(self) -> bool:
        """
        Power off the NAS using the DSM API shutdown command.
        
        Returns:
            bool: True if shutdown command was sent successfully
        """
        logger.info(f"Attempting to shutdown NAS at {self.ip_address}")
        
        if not self.is_online():
            logger.info("NAS is already offline")
            return True
        
        if not self._authenticate():
            logger.error("Failed to authenticate for shutdown")
            return False
        
        try:
            shutdown_url = f"{self.base_url}/webapi/entry.cgi"
            params = {
                'api': 'SYNO.Core.System',
                'version': '1',  # Version 1 works according to tests
                'method': 'shutdown',
                '_sid': self.session_id
            }
            
            response = requests.get(shutdown_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data.get('success'):
                logger.info("Shutdown command sent successfully")
                return True
            else:
                logger.error(f"Shutdown failed: {data.get('error', {})}")
                return False
                
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
            return False
        finally:
            self._logout()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the NAS.
        
        Returns:
            dict: Status information including online status and system info
        """
        status = {
            'online': self.is_online(),
            'ip_address': self.ip_address,
            'mac_address': self.mac_address,
            'ethernet_port': self.ethernet_port,
            'ethernet_active': self._is_ethernet_port_active(),
            'timestamp': time.time()
        }
        
        if status['online'] and self._authenticate():
            try:
                info_url = f"{self.base_url}/webapi/entry.cgi"
                params = {
                    'api': 'SYNO.Core.System',
                    'version': '3',
                    'method': 'info',
                    '_sid': self.session_id
                }
                
                response = requests.get(info_url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        status['system_info'] = data.get('data', {})
                        
            except Exception as e:
                logger.warning(f"Failed to get system info: {e}")
            finally:
                self._logout()
        
        return status


if __name__ == "__main__":
    import sys
    
    def print_usage():
        """Print usage information."""
        print("Usage:")
        print("  python synology_nas_controller.py [config_file] status")
        print("  python synology_nas_controller.py [config_file] power-on")
        print("  python synology_nas_controller.py [config_file] power-off")
        print("  python synology_nas_controller.py [config_file] create-config")
        print("")
        print("Examples:")
        print("  python synology_nas_controller.py status                    # Check NAS status")
        print("  python synology_nas_controller.py power-on                  # Power on NAS")
        print("  python synology_nas_controller.py power-off                 # Power off NAS")
        print("  python synology_nas_controller.py create-config             # Create config template")
        print("  python synology_nas_controller.py /path/config.json status  # Use custom config")
    
    def main():
        """Main command-line interface."""
        # Configure logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        
        args = sys.argv[1:]
        
        # Determine if first argument is a config file path
        config_file = None
        command_args = args
        
        if len(args) >= 1:
            # Check if first arg looks like a file path (contains / or ends with .json)
            if ('/' in args[0] or args[0].endswith('.json')) and args[0] not in ['status', 'power-on', 'power-off', 'create-config']:
                config_file = args[0]
                command_args = args[1:]
        
        if len(command_args) == 0:
            print_usage()
            sys.exit(1)
        
        command = command_args[0].lower()
        
        if command == 'create-config':
            try:
                SynologyNASController.create_config_template(config_file or 'synology_nas_config.json')
                sys.exit(0)
            except Exception as e:
                print(f"ERROR: Failed to create config template: {e}")
                sys.exit(1)
        
        # For all other commands, we need to create the controller
        try:
            nas = SynologyNASController(config_file=config_file)
            
            if command == 'status':
                status = nas.get_status()
                print(f"NAS Status:")
                print(f"  Online: {status['online']}")
                print(f"  IP: {status['ip_address']}")
                print(f"  MAC: {status['mac_address']}")
                print(f"  Ethernet Port: {status['ethernet_port']}")
                print(f"  Ethernet Active: {status['ethernet_active']}")
                if 'system_info' in status:
                    print(f"  System Info: {status['system_info']}")
            
            elif command == 'power-on':
                print("Sending power-on command...")
                result = nas.power_on()
                print(f"Power-on {'successful' if result else 'failed'}")
            
            elif command == 'power-off':
                print("WARNING: This will shut down the NAS!")
                try:
                    confirm = input("Are you sure? (yes/no): ")
                    if confirm.lower() == 'yes':
                        print("Sending shutdown command...")
                        result = nas.power_off()
                        print(f"Shutdown {'successful' if result else 'failed'}")
                    else:
                        print("Shutdown cancelled")
                except KeyboardInterrupt:
                    print("\nShutdown cancelled by user (Ctrl+C)")
                    sys.exit(0)
            
            else:
                print(f"ERROR: Unknown command '{command}'")
                print_usage()
                sys.exit(1)
        
        except ValueError as e:
            print(f"Configuration error: {e}")
            print("\nTo create a config template, run:")
            print("python synology_nas_controller.py create-config")
            sys.exit(1)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user (Ctrl+C)")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: {e}")
            sys.exit(1)
    
    main()
