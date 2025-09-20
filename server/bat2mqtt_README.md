# bat2mqtt.py - Simplified BLE to MQTT Bridge

## Overview

This is a simplified version of `bat2mqtt.py` designed to resolve Docker duplicate output issues by operating sequentially without threads or subprocesses.

## Features

- **Sequential Operation**: Operates in a simple loop without threading or subprocesses
- **BLE Device Support**: Connects to BLE devices using the hci1 adapter (USB connected)
- **MQTT Publishing**: Publishes battery data to MQTT broker
- **Encoding Handling**: Properly handles special characters (like checkmarks) with UTF-8 encoding
- **Docker Compatible**: Designed to work correctly in Docker containers without duplicate output
- **Configurable Debug Levels**: 0=silent, 1=basic, 2=verbose, 3=full debug

## Usage

### Command Line

```bash
# Basic usage with defaults
python3 bat2mqtt.py

# Custom broker and topic
python3 bat2mqtt.py --broker 192.168.1.100 --topic "RV/BATTERY"

# With debug output
python3 bat2mqtt.py --debug 2

# Full options
python3 bat2mqtt.py --broker localhost --port 1883 --topic "RVC/BATTERY_STATUS" --debug 1
```

### Docker

```bash
# Run in Docker container
docker run rvsecurity-image python3 bat2mqtt.py --debug 1
```

## Sequential Operation Flow

The program follows this exact sequence to avoid Docker duplicate output issues:

1. **Wait for complete message** - Scans for and connects to BLE device
2. **Decode the message** - Reads battery data from BLE characteristics  
3. **Publish to MQTT** - Sends decoded data to MQTT broker
4. **Repeat** - Returns to step 1

No threads or subprocesses are used, ensuring clean output in Docker environments.

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `--broker` | localhost | MQTT broker hostname |
| `--port` | 1883 | MQTT broker port |
| `--topic` | RVC/BATTERY_STATUS | MQTT topic for publishing |
| `--debug` | 1 | Debug level (0-3) |

## BLE Device Support

- Uses `hci1` adapter (USB connected BLE device)
- Automatically discovers battery-related devices
- Supports standard Battery Service (UUID 0x180F)
- Handles multiple characteristics gracefully

## MQTT Data Format

Published data follows this JSON structure:

```json
{
  "name": "BATTERY_STATUS",
  "instance": 1,
  "State_of_charge": 75,
  "DC_voltage": 12.3,
  "DC_current": -2.1,
  "status": "Connected",
  "timestamp": 1234567890.123
}
```

## Error Handling

- Graceful handling of BLE connection failures
- MQTT connection retry logic
- Proper UTF-8 encoding for special characters
- Signal handling for clean shutdown

## Testing

The implementation has been tested for:
- ✅ Sequential operation without threads
- ✅ No duplicate output in any environment
- ✅ Proper encoding of special characters
- ✅ Command line argument parsing
- ✅ MQTT publishing functionality
- ✅ Container environment compatibility

## Dependencies

- `bleak==0.21.1` - BLE device communication
- `paho-mqtt==1.6.1` - MQTT client functionality
- Python 3.11+ - Async/await support