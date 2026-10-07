"""Config flow for Strata."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SSL
from homeassistant.core import callback
from homeassistant.helpers import llm
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    TemplateSelector,
)

from .api import StrataAuthError, StrataClient, StrataConnectionError, StrataError
from .const import (
    CONF_API_KEY,
    CONF_LLM_HASS_API,
    CONF_MAX_TOKENS,
    CONF_MAX_TOOL_ITERATIONS,
    CONF_PROMPT,
    CONF_SCAN_INTERVAL,
    CONF_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_ITERATIONS,
    DEFAULT_PORT,
    DEFAULT_PROMPT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)


class StrataConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Strata."""

    VERSION = 1

    async def _validate(self, data: dict[str, Any]) -> tuple[dict[str, str], str | None]:
        client = StrataClient(
            async_get_clientsession(self.hass),
            data[CONF_HOST],
            data[CONF_PORT],
            data.get(CONF_API_KEY) or None,
            data.get(CONF_SSL, False),
        )
        try:
            health = await client.health()
            if health.get("service") != "strata":
                return {"base": "not_strata"}, None
            # /v1/status needs the key when one is configured.
            await client.status()
        except StrataAuthError:
            return {"base": "invalid_auth"}, None
        except StrataConnectionError:
            return {"base": "cannot_connect"}, None
        except StrataError:
            return {"base": "unknown"}, None
        return {}, health.get("model")

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            user_input = {**user_input, CONF_PORT: int(user_input[CONF_PORT])}
            self._async_abort_entries_match(
                {CONF_HOST: user_input[CONF_HOST], CONF_PORT: user_input[CONF_PORT]}
            )
            errors, model = await self._validate(user_input)
            if not errors:
                return self.async_create_entry(
                    title=f"Strata ({user_input[CONF_HOST]})", data=user_input
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                    vol.Optional(CONF_API_KEY): str,
                    vol.Optional(CONF_SSL, default=False): bool,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            errors, _ = await self._validate({**entry.data, **user_input})
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates=user_input
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_API_KEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return StrataOptionsFlow()


class StrataOptionsFlow(OptionsFlow):
    """Conversation agent and polling options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            if not user_input.get(CONF_LLM_HASS_API):
                user_input.pop(CONF_LLM_HASS_API, None)
            return self.async_create_entry(data=user_input)

        opts = self.config_entry.options
        apis = [
            SelectOptionDict(label=api.name, value=api.id)
            for api in llm.async_get_apis(self.hass)
        ]
        schema: dict[Any, Any] = {
            vol.Optional(
                CONF_PROMPT,
                description={"suggested_value": opts.get(CONF_PROMPT, DEFAULT_PROMPT)},
            ): TemplateSelector(),
            vol.Optional(
                CONF_LLM_HASS_API,
                description={"suggested_value": opts.get(CONF_LLM_HASS_API)},
            ): SelectSelector(SelectSelectorConfig(options=apis, multiple=True)),
            vol.Optional(
                CONF_MAX_TOKENS, default=opts.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)
            ): NumberSelector(NumberSelectorConfig(min=16, max=32768, step=16)),
            vol.Optional(
                CONF_TEMPERATURE, default=opts.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)
            ): NumberSelector(NumberSelectorConfig(min=0, max=2, step=0.05)),
            vol.Optional(
                CONF_MAX_TOOL_ITERATIONS,
                default=opts.get(CONF_MAX_TOOL_ITERATIONS, DEFAULT_MAX_TOOL_ITERATIONS),
            ): NumberSelector(NumberSelectorConfig(min=1, max=20, step=1)),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): NumberSelector(NumberSelectorConfig(min=2, max=300, step=1)),
        }
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
