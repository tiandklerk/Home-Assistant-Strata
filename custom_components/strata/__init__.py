"""The Strata integration: a local LLM server for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import StrataAuthError, StrataClient, StrataError
from .const import CONF_API_KEY, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CONVERSATION,
    Platform.SENSOR,
]


@dataclass
class StrataData:
    """Runtime data of one config entry."""

    client: StrataClient
    coordinator: "StrataCoordinator"


type StrataConfigEntry = ConfigEntry[StrataData]


class StrataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll /v1/status and /metrics."""

    config_entry: StrataConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: StrataConfigEntry, client: StrataClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            status = await self.client.status()
        except StrataAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except StrataError as err:
            raise UpdateFailed(f"Cannot reach Strata: {err}") from err
        try:
            metrics = await self.client.metrics()
        except StrataAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except StrataError:
            # /metrics is optional: older servers do not have it.
            metrics = {}
        return {"status": status, "metrics": metrics}


async def async_setup_entry(hass: HomeAssistant, entry: StrataConfigEntry) -> bool:
    """Set up Strata from a config entry."""
    client = StrataClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_API_KEY),
        entry.data.get(CONF_SSL, False),
    )
    coordinator = StrataCoordinator(hass, entry, client)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:  # noqa: BLE001
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = StrataData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: StrataConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: StrataConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
