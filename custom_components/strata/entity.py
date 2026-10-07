"""Base entity."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import StrataConfigEntry, StrataCoordinator
from .const import DOMAIN, NAME


class StrataEntity(CoordinatorEntity[StrataCoordinator]):
    """An entity that belongs to the Strata device."""

    _attr_has_entity_name = True

    def __init__(self, entry: StrataConfigEntry, key: str) -> None:
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        status = self.coordinator.data.get("status", {}) if self.coordinator.data else {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=NAME,
            model=status.get("model"),
            sw_version=status.get("engine"),
            configuration_url=entry.runtime_data.client.base_url,
        )
