"""DataUpdateCoordinator for Innova Butler."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InnovaButlerApi, InnovaButlerApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


class InnovaButlerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage data fetching from Innova Butler API.

    ``data`` is a dict with two keys:
      - ``devices``: list of device dicts (each may carry a ``humidity`` value)
      - ``homes``: list of home dicts (with the current season ``mode``)
    """

    def __init__(self, hass: HomeAssistant, api: InnovaButlerApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            data = await self.api.async_get_data()
            devices = self.api.parse_devices(data)
            homes = self.api.parse_homes(data)
            await self._async_add_humidity(devices)
            return {"devices": devices, "homes": homes}
        except InnovaButlerApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

    async def _async_add_humidity(self, devices: list[dict[str, Any]]) -> None:
        """Fetch per-device humidity via getSettings and attach it in place."""

        async def _fetch(device: dict[str, Any]) -> None:
            device.setdefault("humidity", None)
            firmware_uid = device.get("firmware_uid")
            device_type = device.get("type")
            if not firmware_uid or not device_type:
                return
            try:
                settings = await self.api.async_get_settings(
                    firmware_uid, device_type
                )
            except InnovaButlerApiError as err:
                # Humidity is best-effort: don't fail the whole update and
                # keep the last known value (None if never read).
                _LOGGER.debug(
                    "Could not fetch humidity for %s: %s",
                    device.get("name"),
                    err,
                )
                return
            humidity = self.api.parse_humidity(settings)
            if humidity is not None:
                device["humidity"] = humidity

        await asyncio.gather(*(_fetch(device) for device in devices))
