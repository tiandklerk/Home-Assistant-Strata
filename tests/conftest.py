"""Fixtures."""

import pytest
from homeassistant.setup import async_setup_component

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
async def setup_environment(hass, enable_custom_integrations):
    """Conversation needs the core `homeassistant` component (exposed entities)."""
    assert await async_setup_component(hass, "homeassistant", {})
    yield
