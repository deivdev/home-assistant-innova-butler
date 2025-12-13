"""Climate platform for Innova Butler integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import InnovaButlerConfigEntry
from .const import DOMAIN
from .coordinator import InnovaButlerCoordinator
from . import _LOGGER # Import _LOGGER from __init__.py


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InnovaButlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Innova Butler climate entities."""
    coordinator = entry.runtime_data

    entities = [
        InnovaButlerClimate(coordinator, device)
        for device in coordinator.data
    ]

    async_add_entities(entities)


# Preset mapping for cooling mode
PRESET_HOME = "home"
PRESET_SLEEP = "sleep"
PRESET_ECO = "eco"
PRESET_BOOST = "boost"

COOLING_PRESETS = [PRESET_HOME, PRESET_SLEEP, PRESET_ECO, PRESET_BOOST]

# Map function values to preset names
FUNCTION_TO_PRESET = {
    1: PRESET_HOME,
    2: PRESET_SLEEP,
    3: PRESET_ECO,
    4: PRESET_BOOST,
}

PRESET_TO_FUNCTION = {v: k for k, v in FUNCTION_TO_PRESET.items()}


class InnovaButlerClimate(CoordinatorEntity[InnovaButlerCoordinator], ClimateEntity):
    """Representation of an Innova Butler thermostat."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        coordinator: InnovaButlerCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator)
        self._device_uid = device["uid"]
        self._attr_unique_id = f"{DOMAIN}_{device['unique_id']}"
        self._attr_min_temp = device.get("min_temp", 5)
        self._attr_max_temp = device.get("max_temp", 40)
        self._home_mode = device.get("home_mode", 0)  # 0=heating, 1=cooling
        self._function = device.get("function", 1)  # Current preset function

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["unique_id"])},
            name=device["name"],
            manufacturer="Innova",
            model=device.get("type", "FCL485"),
            suggested_area=device.get("room"),
        )

        self._update_from_device(device)

    def _get_device(self) -> dict[str, Any] | None:
        """Get current device data from coordinator."""
        for device in self.coordinator.data:
            if device["uid"] == self._device_uid:
                return device
        return None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        device = self._get_device()
        if device:
            self._update_from_device(device)
        self.async_write_ha_state()

    def _update_from_device(self, device: dict[str, Any]) -> None:
        """Update entity attributes from device data."""
        self._attr_current_temperature = device.get("temp_room")
        self._attr_target_temperature = device.get("temp_set")
        self._home_mode = device.get("home_mode", 0)
        self._function = device.get("function", 1)

        # Determine HVAC mode
        standby = device.get("standby", False)
        if standby:
            self._attr_hvac_mode = HVACMode.OFF
        else:
            # When the device is on, show actual operating mode (HEAT/COOL)
            if self._home_mode == 0:
                self._attr_hvac_mode = HVACMode.HEAT
            else:
                self._attr_hvac_mode = HVACMode.COOL

        # Connection status
        self._attr_available = device.get("connected", True)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        """Return supported features based on current mode."""
        features = (
            ClimateEntityFeature.TARGET_TEMPERATURE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        # Add preset support only in cooling mode
        if self._home_mode == 1:
            features |= ClimateEntityFeature.PRESET_MODE
        return features

    @property
    def hvac_modes(self) -> list[HVACMode]:
        """Return available HVAC modes based on home mode."""
        if self._home_mode == 0:
            return [HVACMode.OFF, HVACMode.HEAT]
        else:
            return [HVACMode.OFF, HVACMode.COOL]

    @property
    def preset_modes(self) -> list[str] | None:
        """Return available preset modes (only in cooling mode)."""
        if self._home_mode == 1:
            return COOLING_PRESETS
        return None

    @property
    def preset_mode(self) -> str | None:
        """Return current preset mode (only in cooling mode)."""
        if self._home_mode == 1:
            return FUNCTION_TO_PRESET.get(self._function, PRESET_HOME)
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            _LOGGER.error("Missing target temperature for set_temperature")
            return

        await self.coordinator.api.async_set_temperature(self._device_uid, temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        if hvac_mode == HVACMode.OFF:
            await self.coordinator.api.async_power_off_device(self._device_uid)
        elif hvac_mode in (HVACMode.HEAT, HVACMode.COOL):
            # HEAT/COOL mode is determined by home setting, selecting either turns on device
            await self.coordinator.api.async_power_on_device(self._device_uid)
        else:
            _LOGGER.warning("Unsupported HVAC mode selected: %s", hvac_mode)
            return
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode (only in cooling mode)."""
        if self._home_mode != 1:
            _LOGGER.warning("Preset modes only available in cooling mode")
            return

        function = PRESET_TO_FUNCTION.get(preset_mode)
        if function is None:
            _LOGGER.warning("Unknown preset mode: %s", preset_mode)
            return

        await self.coordinator.api.async_set_function(self._device_uid, function)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self) -> None:
        """Turn on the device."""
        await self.coordinator.api.async_power_on_device(self._device_uid)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        """Turn off the device."""
        await self.coordinator.api.async_power_off_device(self._device_uid)
        await self.coordinator.async_request_refresh()
