"""Sensors for Strata."""

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
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfInformation,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StrataConfigEntry
from .entity import StrataEntity


def _machine(data: dict[str, Any], section: str, key: str) -> Any:
    return ((data["status"].get("machine") or {}).get(section) or {}).get(key)


def _live(data: dict[str, Any], key: str) -> Any:
    return (data["metrics"].get("live") or {}).get(key)


@dataclass(frozen=True, kw_only=True)
class StrataSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]


SENSORS: tuple[StrataSensorDescription, ...] = (
    StrataSensorDescription(
        key="state",
        translation_key="state",
        device_class=SensorDeviceClass.ENUM,
        options=["unloaded", "idle", "reading", "generating"],
        value_fn=lambda d: _live(d, "state")
        or ("idle" if d["status"].get("loaded") else "unloaded"),
    ),
    StrataSensorDescription(
        key="model",
        translation_key="model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d["status"].get("model"),
    ),
    StrataSensorDescription(
        key="tokens_per_second",
        translation_key="tokens_per_second",
        native_unit_of_measurement="tok/s",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _live(d, "tok_s")
        or ((d["status"].get("last_timings") or {}).get("predicted_per_second")),
    ),
    StrataSensorDescription(
        key="prompt_tokens_per_second",
        translation_key="prompt_tokens_per_second",
        native_unit_of_measurement="tok/s",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (d["status"].get("last_timings") or {}).get(
            "prompt_per_second"
        ),
    ),
    StrataSensorDescription(
        key="requests",
        translation_key="requests",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: (d["status"].get("activity") or {}).get("requests"),
    ),
    StrataSensorDescription(
        key="queued",
        translation_key="queued",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _live(d, "queued"),
    ),
    StrataSensorDescription(
        key="context",
        translation_key="context",
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement="tokens",
        value_fn=lambda d: (d["status"].get("context") or {}).get("native"),
    ),
    StrataSensorDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d["status"].get("uptime_s"),
    ),
    StrataSensorDescription(
        key="gpu_utilization",
        translation_key="gpu_utilization",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _machine(d, "gpu", "util_pct"),
    ),
    StrataSensorDescription(
        key="gpu_temperature",
        translation_key="gpu_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _machine(d, "gpu", "temp_c"),
    ),
    StrataSensorDescription(
        key="gpu_power",
        translation_key="gpu_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _machine(d, "gpu", "power_w"),
    ),
    StrataSensorDescription(
        key="vram_used",
        translation_key="vram_used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _machine(d, "gpu", "used_mib"),
    ),
    StrataSensorDescription(
        key="ram_used",
        translation_key="ram_used",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.GIBIBYTES,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _machine(d, "ram", "used_gib"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StrataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities(StrataSensor(entry, desc) for desc in SENSORS)


class StrataSensor(StrataEntity, SensorEntity):
    entity_description: StrataSensorDescription

    def __init__(self, entry: StrataConfigEntry, description: StrataSensorDescription) -> None:
        super().__init__(entry, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
