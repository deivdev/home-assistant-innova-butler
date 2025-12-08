"""Innova Butler integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InnovaButlerApi
from .const import CONF_HOST, DOMAIN, PLATFORMS
from .coordinator import InnovaButlerCoordinator

_LOGGER = logging.getLogger(__name__)

type InnovaButlerConfigEntry = ConfigEntry[InnovaButlerCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: InnovaButlerConfigEntry) -> bool:
    """Set up Innova Butler from a config entry."""
    host = entry.data[CONF_HOST]
    session = async_get_clientsession(hass)

    api = InnovaButlerApi(host, session)
    coordinator = InnovaButlerCoordinator(hass, api)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: InnovaButlerConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
