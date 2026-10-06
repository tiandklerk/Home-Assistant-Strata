"""Constants for the Strata integration."""

from __future__ import annotations

DOMAIN = "strata"
NAME = "Strata"

CONF_API_KEY = "api_key"
CONF_PROMPT = "prompt"
CONF_MAX_TOKENS = "max_tokens"
CONF_TEMPERATURE = "temperature"
CONF_LLM_HASS_API = "llm_hass_api"
CONF_MAX_TOOL_ITERATIONS = "max_tool_iterations"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8080
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOOL_ITERATIONS = 8
DEFAULT_SCAN_INTERVAL = 10
# Strata reads a long prompt and may load the model first, so be patient.
REQUEST_TIMEOUT = 300
DEFAULT_PROMPT = (
    "You are a voice assistant for Home Assistant. "
    "Answer in plain, short sentences without markdown."
)
