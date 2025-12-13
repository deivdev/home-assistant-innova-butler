# Innova Butler

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Home Assistant integration for **Innova Butler** climate control systems.

## Features

- Climate entities for each thermostat/fan coil
- Current temperature reading
- Target temperature control
- HVAC mode control (Heat/Cool/Off)
- Auto-discovery of all devices in your Innova system

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on **Integrations**
3. Click the three dots menu (top right) → **Custom repositories**
4. Add this repository URL: `https://github.com/deivdev/home-assistant-innova-butler`
5. Select category: **Integration**
6. Click **Add**
7. Search for "Innova Butler" and install it
8. Restart Home Assistant

### Manual Installation

1. Download the `custom_components/innova_butler` folder
2. Copy it to your Home Assistant `config/custom_components/` directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Innova Butler"
4. Enter the IP address of your Innova Butler device
5. Click **Submit**

The integration will automatically discover all thermostats and fan coils connected to your system.

## Supported Devices

- Innova Butler hub/gateway
- FCL485 fan coil controllers
- Compatible Innova thermostats

## Requirements

- Home Assistant 2024.9.0 or newer
- Innova Butler device accessible on your local network

## Troubleshooting

### Cannot connect to device

- Verify the IP address is correct
- Ensure the Innova Butler device is powered on and connected to your network
- Check that Home Assistant can reach the device (same network/VLAN)

### No devices found

- Make sure your thermostats are properly configured in the Innova app
- Check that devices appear in the Innova web interface

## License

This project is licensed under the MIT License.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.
