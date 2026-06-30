"""API client for Innova Butler."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

API_PATH = "/installedplugin/com.innova.ambiente/2.0/server/index.php"

GET_HOMEPAGE_ACTION = "getHomepage"
GET_SETTINGS_ACTION = "getSettings"
SET_SETPOINT_ACTION = "setSetPoint"
POWER_OFF_DEVICE_ACTION = "powerOffDevice"
POWER_ON_DEVICE_ACTION = "powerOnDevice"
SET_FUNCTION_ACTION = "setFunction"
SET_MODE_HOME_ACTION = "setModeHome"

# Home season modes (home-level)
HOME_MODE_HEATING = 0
HOME_MODE_COOLING = 1

REQUEST_TIMEOUT = 10


class InnovaButlerApiError(Exception):
    """Exception for API errors."""


class InnovaButlerApi:
    """API client for Innova Butler thermostats.

    The Innova Ambiente local server accepts both read and write requests
    over the LAN without session authentication, so no login/token handling
    is required here.
    """

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the API client."""
        self._host = host
        self._session = session
        self._base_url = f"http://{host}{API_PATH}"

    async def _async_request(
        self,
        action: str,
        *,
        method: str = "GET",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Perform an HTTP request to the Innova local server."""
        url = f"{self._base_url}?Action={action}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(method, url, data=data) as response:
                    if response.status != 200:
                        raise InnovaButlerApiError(
                            f"API '{action}' returned status {response.status}"
                        )
                    json_response = await response.json(content_type=None)

            if not json_response.get("success"):
                raise InnovaButlerApiError(f"API '{action}' returned success=false")

            return json_response

        except asyncio.TimeoutError as err:
            raise InnovaButlerApiError(
                f"Timeout on '{action}' to {self._host}"
            ) from err
        except aiohttp.ClientError as err:
            raise InnovaButlerApiError(
                f"Error on '{action}' to {self._host}: {err}"
            ) from err

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch the homepage data from the API."""
        return await self._async_request(GET_HOMEPAGE_ACTION)

    async def async_get_settings(
        self, firmware_uid: str, device_type: str
    ) -> dict[str, Any]:
        """Fetch detailed settings for a device (includes humidity)."""
        data = {"uid": firmware_uid, "type": device_type, "plugin": ""}
        return await self._async_request(
            GET_SETTINGS_ACTION, method="POST", data=data
        )

    async def async_set_temperature(
        self, device_uid: str, temperature: float
    ) -> None:
        """Set the target temperature for a device."""
        await self._async_request(
            SET_SETPOINT_ACTION,
            method="POST",
            data={"deviceUid": device_uid, "value": str(temperature)},
        )

    async def async_power_off_device(self, device_uid: str) -> None:
        """Power off the device."""
        await self._async_request(
            POWER_OFF_DEVICE_ACTION,
            method="POST",
            data={"deviceUid": device_uid, "value": "0"},
        )

    async def async_power_on_device(self, device_uid: str) -> None:
        """Power on the device."""
        await self._async_request(
            POWER_ON_DEVICE_ACTION,
            method="POST",
            data={"deviceUid": device_uid, "value": "1"},
        )

    async def async_set_function(self, device_uid: str, function: int) -> None:
        """Set the function/preset for a device."""
        await self._async_request(
            SET_FUNCTION_ACTION,
            method="POST",
            data={"deviceUid": device_uid, "function": str(function)},
        )

    async def async_set_home_mode(self, home_uid: str, mode: int) -> None:
        """Set the home season mode (0=heating, 1=cooling)."""
        await self._async_request(
            SET_MODE_HOME_ACTION,
            method="POST",
            data={"homeUid": home_uid, "mode": str(mode)},
        )

    def parse_homes(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse homes (with their season mode) from API response."""
        homes = []
        try:
            for home in data.get("RESULT", {}).get("user", {}).get("homes", []):
                homes.append(
                    {
                        "uid": home.get("uid"),
                        "unique_id": home.get("uniqueID", home.get("uid")),
                        "name": home.get("name", ""),
                        "mode": home.get("mode", 0),  # 0=heating, 1=cooling
                    }
                )
        except (KeyError, TypeError) as err:
            _LOGGER.error("Error parsing homes: %s", err)
        return homes

    def parse_devices(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse devices from API response."""
        devices = []
        try:
            homes = data.get("RESULT", {}).get("user", {}).get("homes", [])
            for home in homes:
                home_name = home.get("name", "")
                home_uid = home.get("uid")
                home_mode = home.get("mode", 0)  # 0=heating, 1=cooling
                for room in home.get("rooms", []):
                    room_name = room.get("name", "")
                    for device_uid, device in room.get("devices", {}).items():
                        devices.append({
                            "uid": device.get("uid", device_uid),
                            "unique_id": device.get("uniqueId", device_uid),
                            "firmware_uid": device.get("firmwareUid"),
                            "name": device.get("name", room_name),
                            "room": room_name,
                            "home": home_name,
                            "home_uid": home_uid,
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

    def parse_humidity(self, data: dict[str, Any]) -> float | None:
        """Parse on-board humidity (RH %) from a getSettings response."""
        try:
            radiante = data.get("RESULT", {}).get("settings", {}).get("RADIANTE", [])
            for field in radiante:
                if field.get("fieldName") == "RH":
                    value = field.get("fieldValue")
                    if value in (None, ""):
                        return None
                    return float(value)
        except (KeyError, TypeError, ValueError) as err:
            _LOGGER.debug("Error parsing humidity: %s", err)
        return None

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
