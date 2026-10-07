"""Smoke tests against a mocked Strata server."""

from homeassistant.components import conversation
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import Context, HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.strata.const import DOMAIN

BASE = "http://10.0.0.5:8080"
STATUS = {
    "service": "strata", "model": "qwen", "loaded": True, "engine": "0.1.36",
    "uptime_s": 120, "context": {"native": 131072},
    "activity": {"requests": 7, "in_flight": 0},
    "last_timings": {"predicted_per_second": 55.5, "prompt_per_second": 1600.0},
    "machine": {"gpu": {"name": "RTX", "used_mib": 11000, "util_pct": 80, "temp_c": 61, "power_w": 200},
                "ram": {"used_gib": 40.2, "total_gib": 64}},
}
METRICS = {"live": {"state": "idle", "queued": 0}}


def _mock(aioclient_mock):
    aioclient_mock.get(f"{BASE}/health", json={"service": "strata", "model": "qwen"})
    aioclient_mock.get(f"{BASE}/v1/status", json=STATUS)
    aioclient_mock.get(f"{BASE}/metrics", json=METRICS)


async def test_flow_and_entities(hass: HomeAssistant, aioclient_mock) -> None:
    _mock(aioclient_mock)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get("sensor.strata_10_0_0_5_answer_speed").state == "55.5"
    assert hass.states.get("sensor.strata_10_0_0_5_gpu_temperature").state == "61"
    assert hass.states.get("binary_sensor.strata_10_0_0_5_model_loaded").state == "on"
    assert hass.states.get("binary_sensor.strata_10_0_0_5_busy").state == "off"


async def test_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    import aiohttp
    aioclient_mock.get(f"{BASE}/health", exc=aiohttp.ClientError)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_HOST: "10.0.0.5", CONF_PORT: 8080}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_conversation(hass: HomeAssistant, aioclient_mock) -> None:
    _mock(aioclient_mock)
    aioclient_mock.post(
        f"{BASE}/v1/chat/completions",
        json={"choices": [{"message": {"role": "assistant", "content": "<think>hm</think>Hello!"}}]},
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_HOST: "10.0.0.5", CONF_PORT: 8080}, title="Strata (10.0.0.5)")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await conversation.async_converse(
        hass, "hi", None, Context(),
        agent_id="conversation.strata_10_0_0_5",
    )
    assert result.response.speech["plain"]["speech"] == "Hello!"
