"""Binary sensors for Strata."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StrataConfigEntry
from .entity import StrataEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StrataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([StrataLoaded(entry), StrataBusy(entry)])


class StrataLoaded(StrataEntity, BinarySensorEntity):
    """The model is loaded on the GPU."""

    _attr_translation_key = "loaded"

    def __init__(self, entry: StrataConfigEntry) -> None:
        super().__init__(entry, "loaded")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data["status"].get("loaded"))


class StrataBusy(StrataEntity, BinarySensorEntity):
    """The model is reading a prompt or writing an answer."""

    _attr_translation_key = "busy"
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, entry: StrataConfigEntry) -> None:
        super().__init__(entry, "busy")

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        live = (data["metrics"].get("live") or {}).get("state")
        if live is not None:
            return live in ("reading", "generating")
        return ((data["status"].get("activity") or {}).get("in_flight") or 0) > 0
