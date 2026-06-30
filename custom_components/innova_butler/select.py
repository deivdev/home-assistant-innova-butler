"""Select platform for Innova Butler integration (home season mode)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import InnovaButlerConfigEntry
from .api import HOME_MODE_COOLING, HOME_MODE_HEATING
from .const import DOMAIN
from .coordinator import InnovaButlerCoordinator

SEASON_HEATING = "heating"
SEASON_COOLING = "cooling"

OPTION_TO_MODE = {
    SEASON_HEATING: HOME_MODE_HEATING,
    SEASON_COOLING: HOME_MODE_COOLING,
}
MODE_TO_OPTION = {v: k for k, v in OPTION_TO_MODE.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InnovaButlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Innova Butler home season selectors."""
    coordinator = entry.runtime_data

    entities = [
        InnovaButlerSeasonSelect(coordinator, home)
        for home in coordinator.data["homes"]
        if home.get("uid")
    ]

    async_add_entities(entities)


class InnovaButlerSeasonSelect(
    CoordinatorEntity[InnovaButlerCoordinator], SelectEntity
):
    """Home season selector (heating/cooling) for an Innova Butler home."""

    _attr_has_entity_name = True
    _attr_translation_key = "season"
    _attr_options = [SEASON_HEATING, SEASON_COOLING]

    def __init__(
        self,
        coordinator: InnovaButlerCoordinator,
        home: dict[str, Any],
    ) -> None:
        """Initialize the season selector."""
        super().__init__(coordinator)
        self._home_uid = home["uid"]
        self._attr_unique_id = f"{DOMAIN}_{home['unique_id']}_season"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"home_{home['unique_id']}")},
            name=home["name"],
            manufacturer="Innova",
            model="Butler Home",
        )

    def _get_home(self) -> dict[str, Any] | None:
        """Get current home data from coordinator."""
        for home in self.coordinator.data["homes"]:
            if home["uid"] == self._home_uid:
                return home
        return None

    @property
    def current_option(self) -> str | None:
        """Return the current season."""
        home = self._get_home()
        if home is None:
            return None
        return MODE_TO_OPTION.get(home.get("mode", HOME_MODE_HEATING))

    async def async_select_option(self, option: str) -> None:
        """Change the home season mode."""
        mode = OPTION_TO_MODE.get(option)
        if mode is None:
            return
        await self.coordinator.api.async_set_home_mode(self._home_uid, mode)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
