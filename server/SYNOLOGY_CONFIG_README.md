# Synology NAS Controller Configuration

This controller manages your Synology DS620slim NAS with secure credential handling.

## Security Best Practices

**⚠️ IMPORTANT: Never commit credentials to version control!**

## Configuration Options (in order of priority)

### 1. Environment Variables (Recommended for production)
```bash
export SYNOLOGY_IP="192.168.1.100"
export SYNOLOGY_MAC="00:11:32:44:55:66"
export SYNOLOGY_USER="admin"
export SYNOLOGY_PASSWORD="your_secure_password"
export SYNOLOGY_PORT="5000"  # Optional, defaults to 5000
```

### 2. Configuration File (Good for development)
```bash
# Create config file from template
python synology_nas_controller.py --create-config

# Edit the created file with your actual credentials
nano synology_nas_config.json
```

The config file is automatically excluded from Git via `.gitignore`.

## Prerequisites

1. **Enable Wake-on-LAN on your NAS:**
   - Log into DSM
   - Go to Control Panel > Hardware & Power > General
   - Check "Enable Wake on LAN"

2. **Find your NAS MAC address:**
   - DSM > Control Panel > Info Center > Network
   - Or use: `arp -a | grep [ip_address]`

## Usage Examples

```bash
# Create configuration template
python synology_nas_controller.py --create-config

# Check NAS status
python synology_nas_controller.py --status

# Power on NAS
python synology_nas_controller.py --power-on

# Power off NAS (with confirmation)
python synology_nas_controller.py --power-off

# Use custom config file
python synology_nas_controller.py --config /path/to/config.json --status
```

## Integration in Code

```python
from synology_nas_controller import SynologyNASController

# Uses environment variables or default config file
nas = SynologyNASController()

# Or specify a custom config file
nas = SynologyNASController(config_file="/path/to/config.json")

# Power operations
nas.power_on()
status = nas.get_status()
nas.power_off()
```

## Configuration File Locations

The controller looks for config files in this order:
1. Specified config file path
2. `./synology_nas_config.json` (current directory)
3. `~/.config/rvSecurity/synology_nas_config.json` (user config)
4. `/etc/rvSecurity/synology_nas_config.json` (system config)

## Security Notes

- Config files are created with restricted permissions (600)
- The `.gitignore` prevents accidental commits
- Environment variables are the most secure option for production
- Never hardcode credentials in your source code
