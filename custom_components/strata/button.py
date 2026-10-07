"""Buttons to load and unload the model (free the GPU for games)."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StrataConfigEntry
from .api import StrataError
from .entity import StrataEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StrataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([StrataLoadButton(entry), StrataUnloadButton(entry)])


class _StrataButton(StrataEntity, ButtonEntity):
    _action = ""

    def __init__(self, entry: StrataConfigEntry) -> None:
        super().__init__(entry, self._action)
        self._client = entry.runtime_data.client

    async def async_press(self) -> None:
        try:
            await getattr(self._client, self._action)()
        except StrataError as err:
            raise HomeAssistantError(f"Strata could not {self._action} the model: {err}") from err
        await self.coordinator.async_request_refresh()


class StrataLoadButton(_StrataButton):
    _action = "load"
    _attr_translation_key = "load"


class StrataUnloadButton(_StrataButton):
    _action = "unload"
    _attr_translation_key = "unload"
