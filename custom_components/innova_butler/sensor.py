"""Sensor platform for Innova Butler integration (humidity, temperature)."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import InnovaButlerConfigEntry
from .const import DOMAIN
from .coordinator import InnovaButlerCoordinator


@dataclass(frozen=True, kw_only=True)
class InnovaButlerSensorDescription(SensorEntityDescription):
    """Describes an Innova Butler sensor."""

    value_fn: Callable[[dict[str, Any]], float | None]


SENSOR_DESCRIPTIONS: tuple[InnovaButlerSensorDescription, ...] = (
    InnovaButlerSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda device: device.get("temp_room"),
    ),
    InnovaButlerSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        value_fn=lambda device: device.get("humidity"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: InnovaButlerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Innova Butler sensors."""
    coordinator = entry.runtime_data

    # Create one sensor per (device, description). Sensors report unavailable
    # when their value is temporarily missing, rather than being skipped.
    entities = [
        InnovaButlerSensor(coordinator, device, description)
        for device in coordinator.data["devices"]
        if device.get("firmware_uid")
        for description in SENSOR_DESCRIPTIONS
    ]

    async_add_entities(entities)


class InnovaButlerSensor(CoordinatorEntity[InnovaButlerCoordinator], SensorEntity):
    """A sensor (temperature or humidity) for an Innova Butler device."""

    _attr_has_entity_name = True
    entity_description: InnovaButlerSensorDescription

    def __init__(
        self,
        coordinator: InnovaButlerCoordinator,
        device: dict[str, Any],
        description: InnovaButlerSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_uid = device["uid"]
        self._attr_unique_id = f"{DOMAIN}_{device['unique_id']}_{description.key}"

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
        """Return the current sensor value."""
        device = self._get_device()
        if device is None:
            return None
        return self.entity_description.value_fn(device)

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        device = self._get_device()
        return (
            super().available
            and device is not None
            and device.get("connected", True)
            and self.entity_description.value_fn(device) is not None
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()
