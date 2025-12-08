"""DataUpdateCoordinator for Innova Butler."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InnovaButlerApi, InnovaButlerApiError
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=60)


class InnovaButlerCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator to manage data fetching from Innova Butler API."""

    def __init__(self, hass: HomeAssistant, api: InnovaButlerApi) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.api = api

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data from API."""
        try:
            data = await self.api.async_get_data()
            return self.api.parse_devices(data)
        except InnovaButlerApiError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
