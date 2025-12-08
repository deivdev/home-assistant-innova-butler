"""API client for Innova Butler."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_PATH = "/installedplugin/com.innova.ambiente/2.0/server/index.php"

SET_SETPOINT_ACTION = "setSetPoint"
POWER_OFF_DEVICE_ACTION = "powerOffDevice"
POWER_ON_DEVICE_ACTION = "powerOnDevice"


class InnovaButlerApiError(Exception):
    """Exception for API errors."""


class InnovaButlerApi:
    """API client for Innova Butler thermostats."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._host = host
        self._session = session
        self._base_url = f"http://{host}{API_PATH}"

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch data from the API."""
        url = f"{self._base_url}?Action=getHomepage"
        try:
            async with asyncio.timeout(10):
                async with self._session.get(url) as response:
                    if response.status != 200:
                        raise InnovaButlerApiError(
                            f"API returned status {response.status}"
                        )
                    data = await response.json()

            if not data.get("success"):
                raise InnovaButlerApiError("API returned success=false")

            return data

        except asyncio.TimeoutError as err:
            raise InnovaButlerApiError(f"Timeout connecting to {self._host}") from err
        except aiohttp.ClientError as err:
            raise InnovaButlerApiError(f"Error connecting to {self._host}: {err}") from err

    async def _async_send_command(self, action: str, device_uid: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Send a command to the API."""
        url = f"{self._base_url}?Action={action}"
        headers = {
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "it-IT,it;q=0.9,fr-FR;q=0.8,fr;q=0.7,ru-RU;q=0.6,ru;q=0.5,es-ES;q=0.4,es;q=0.3,en-US;q=0.2,en;q=0.1",
            "Connection": "keep-alive",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            # NOTE: KSESS cookie and X-keye headers might need to be dynamic
            # For now, hardcoding based on the provided curl command.
            # In a real scenario, these would likely be obtained during login or
            # from the initial getHomepage response.
#            "Cookie": "KSESS=0e097367-871a-491f-82b6-acca201e4875; KSESS=0e097367-871a-491f-82b6-acca201e4875",
            "DNT": "1",
            "Origin": f"http://{self._host}",
            "Referer": f"http://{self._host}/v/1.0.66.3/plugins/com.innova.ambiente/gui/index.html",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
#            "X-keye-UserID": "3ce06650-dd83-48a0-a85e-391511520318",
#            "x-keye-accessToken": "842a327804153d5388f66fa0d23b419e87679b748614e35f60a10f5df6b24db11e2c4c338ac1ca577bbf842225fee50a",
        }
        data = {
            "deviceUid": device_uid,
            **payload
        }
        
        try:
            async with asyncio.timeout(10):
                async with self._session.post(url, headers=headers, data=data) as response:
                    if response.status != 200:
                        raise InnovaButlerApiError(
                            f"API command '{action}' returned status {response.status}"
                        )
                    json_response = await response.json()

            if not json_response.get("success"):
                raise InnovaButlerApiError(f"API command '{action}' returned success=false")

            return json_response

        except asyncio.TimeoutError as err:
            raise InnovaButlerApiError(f"Timeout sending command '{action}' to {self._host}") from err
        except aiohttp.ClientError as err:
            raise InnovaButlerApiError(f"Error sending command '{action}' to {self._host}: {err}") from err

    async def async_set_temperature(self, device_uid: str, temperature: float) -> None:
        """Set the target temperature for a device."""
        payload = {"value": str(temperature)}
        await self._async_send_command(SET_SETPOINT_ACTION, device_uid, payload)

    async def async_power_off_device(self, device_uid: str) -> None:
        """Power off the device."""
        payload = {"value": "0"} 
        await self._async_send_command(POWER_OFF_DEVICE_ACTION, device_uid, payload)

    async def async_power_on_device(self, device_uid: str) -> None:
        """Power on the device."""
        payload = {"value": "1"} 
        await self._async_send_command(POWER_ON_DEVICE_ACTION, device_uid, payload)

    def parse_devices(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse devices from API response."""
        devices = []
        try:
            homes = data.get("RESULT", {}).get("user", {}).get("homes", [])
            for home in homes:
                home_name = home.get("name", "")
                home_mode = home.get("mode", 0)  # 0=heating, 1=cooling
                for room in home.get("rooms", []):
                    room_name = room.get("name", "")
                    for device_uid, device in room.get("devices", {}).items():
                        devices.append({
                            "uid": device.get("uid", device_uid),
                            "unique_id": device.get("uniqueId", device_uid),
                            "name": device.get("name", room_name),
                            "room": room_name,
                            "home": home_name,
                            "home_mode": home_mode,
                            "type": device.get("type", ""),
                            "temp_room": device.get("tempRoom"),
                            "temp_set": device.get("tempSet"),
                            "standby": self._parse_standby(device.get("standBy", {})),
                            "min_temp": device.get("min", 5),
                            "max_temp": device.get("max", 40),
                            "function": self._parse_function(device.get("settings", {})),
                            "function_options": self._parse_function_options(device.get("settings", {})),
                            "connected": device.get("connectionStatus", {}).get("status") == 1,
                        })
        except (KeyError, TypeError) as err:
            _LOGGER.error("Error parsing devices: %s", err)
        return devices

    def _parse_standby(self, standby: dict[str, Any]) -> bool:
        """Parse standby value (can be bool, string, or int)."""
        value = standby.get("value", 0)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() == "true" or value == "1"
        return bool(value)

    def _parse_function(self, settings: dict[str, Any]) -> int:
        """Parse function/fan mode value."""
        func = settings.get("function", {})
        try:
            return int(func.get("value", 1))
        except (ValueError, TypeError):
            return 1

    def _parse_function_options(self, settings: dict[str, Any]) -> dict[int, str]:
        """Parse function options to map value -> label."""
        func = settings.get("function", {})
        options = {}
        for opt in func.get("fieldOptions", []):
            value = opt.get("value")
            label = opt.get("label", "").replace("FUNCTION_", "").lower()
            if value is not None:
                options[value] = label
        return options
