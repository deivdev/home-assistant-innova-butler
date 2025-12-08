"""Config flow for Innova Butler integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import InnovaButlerApi, InnovaButlerApiError
from .const import CONF_HOST, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)


class InnovaButlerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Innova Butler."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]

            # Check if already configured
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            # Test connection
            session = async_get_clientsession(self.hass)
            api = InnovaButlerApi(host, session)

            try:
                data = await api.async_get_data()
                devices = api.parse_devices(data)
                if not devices:
                    errors["base"] = "no_devices"
                else:
                    # Get home name for title
                    home_name = devices[0].get("home", DEFAULT_NAME)
                    return self.async_create_entry(
                        title=home_name,
                        data=user_input,
                    )
            except InnovaButlerApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
