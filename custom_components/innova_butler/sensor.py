"""Sensor platform for Innova Butler integration (humidity)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import InnovaButlerConfigEntry
from .const import DOMAIN
from .coordinator import InnovaButlerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InnovaButlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Innova Butler humidity sensors."""
    coordinator = entry.runtime_data

    entities = [
        InnovaButlerHumiditySensor(coordinator, device)
        for device in coordinator.data["devices"]
        if device.get("humidity") is not None
    ]

    async_add_entities(entities)


class InnovaButlerHumiditySensor(
    CoordinatorEntity[InnovaButlerCoordinator], SensorEntity
):
    """On-board humidity sensor for an Innova Butler device."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_translation_key = "humidity"

    def __init__(
        self,
        coordinator: InnovaButlerCoordinator,
        device: dict[str, Any],
    ) -> None:
        """Initialize the humidity sensor."""
        super().__init__(coordinator)
        self._device_uid = device["uid"]
        self._attr_unique_id = f"{DOMAIN}_{device['unique_id']}_humidity"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device["unique_id"])},
            name=device["name"],
            manufacturer="Innova",
            model=device.get("type", "FCL485"),
            suggested_area=device.get("room"),
        )

    def _get_device(self) -> dict[str, Any] | None:
        """Get current device data from coordinator."""
        for device in self.coordinator.data["devices"]:
            if device["uid"] == self._device_uid:
                return device
        return None

    @property
    def native_value(self) -> float | None:
        """Return the current humidity."""
        device = self._get_device()
        if device is None:
            return None
        return device.get("humidity")

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        device = self._get_device()
        return (
            super().available
            and device is not None
            and device.get("connected", True)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
