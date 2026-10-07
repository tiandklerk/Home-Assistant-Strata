"""Conversation agent backed by Strata's OpenAI-compatible endpoint."""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from voluptuous_openapi import convert

from homeassistant.components import conversation
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import intent, llm
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import StrataConfigEntry
from .api import StrataError
from .const import (
    CONF_LLM_HASS_API,
    CONF_MAX_TOKENS,
    CONF_MAX_TOOL_ITERATIONS,
    CONF_PROMPT,
    CONF_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_ITERATIONS,
    DEFAULT_PROMPT,
    DEFAULT_TEMPERATURE,
    DOMAIN,
)
from .entity import StrataEntity

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StrataConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([StrataConversationEntity(entry)])


def _format_tool(tool: llm.Tool, custom_serializer: Any) -> dict[str, Any]:
    spec: dict[str, Any] = {"name": tool.name}
    if tool.description:
        spec["description"] = tool.description
    spec["parameters"] = convert(tool.parameters, custom_serializer=custom_serializer)
    return {"type": "function", "function": spec}


def _messages(chat_log: conversation.ChatLog) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in chat_log.content:
        if item.role == "system":
            out.append({"role": "system", "content": item.content})
        elif item.role == "user":
            out.append({"role": "user", "content": item.content})
        elif item.role == "assistant":
            msg: dict[str, Any] = {"role": "assistant", "content": item.content or ""}
            if item.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.tool_name,
                            "arguments": json.dumps(call.tool_args),
                        },
                    }
                    for call in item.tool_calls
                ]
            out.append(msg)
        elif item.role == "tool_result":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": item.tool_call_id,
                    "content": json.dumps(item.tool_result),
                }
            )
    return out


class StrataConversationEntity(
    conversation.ConversationEntity,
    conversation.AbstractConversationAgent,
    StrataEntity,
):
    """Assist conversation agent that talks to the local Strata model."""

    _attr_name = None

    def __init__(self, entry: StrataConfigEntry) -> None:
        super().__init__(entry, "conversation")
        self.entry = entry
        if entry.options.get(CONF_LLM_HASS_API):
            self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def _async_handle_message(
        self,
        user_input: conversation.ConversationInput,
        chat_log: conversation.ChatLog,
    ) -> conversation.ConversationResult:
        options = self.entry.options
        try:
            await chat_log.async_provide_llm_data(
                user_input.as_llm_context(DOMAIN),
                options.get(CONF_LLM_HASS_API) or None,
                options.get(CONF_PROMPT, DEFAULT_PROMPT),
                user_input.extra_system_prompt,
            )
        except conversation.ConverseError as err:
            return err.as_conversation_result()

        client = self.entry.runtime_data.client
        payload: dict[str, Any] = {
            "model": self.coordinator.data["status"].get("model") or "strata",
            "max_tokens": int(options.get(CONF_MAX_TOKENS, DEFAULT_MAX_TOKENS)),
            "temperature": float(options.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE)),
        }
        if chat_log.llm_api:
            payload["tools"] = [
                _format_tool(tool, chat_log.llm_api.custom_serializer)
                for tool in chat_log.llm_api.tools
            ]

        max_iterations = int(
            options.get(CONF_MAX_TOOL_ITERATIONS, DEFAULT_MAX_TOOL_ITERATIONS)
        )
        for _ in range(max_iterations):
            try:
                result = await client.chat({**payload, "messages": _messages(chat_log)})
            except StrataError as err:
                raise HomeAssistantError(f"Error talking to Strata: {err}") from err

            try:
                message = result["choices"][0]["message"]
            except (KeyError, IndexError, TypeError) as err:
                raise HomeAssistantError("Unexpected response from Strata") from err

            text = _THINK_RE.sub("", message.get("content") or "").strip()
            tool_calls: list[llm.ToolInput] = []
            for call in message.get("tool_calls") or []:
                fn = call.get("function") or {}
                raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw) if isinstance(raw, str) else dict(raw)
                except (ValueError, TypeError):
                    args = {}
                tool_calls.append(
                    llm.ToolInput(
                        id=call.get("id") or f"call_{len(tool_calls)}",
                        tool_name=fn.get("name", ""),
                        tool_args=args,
                    )
                )

            content = conversation.AssistantContent(
                agent_id=self.entity_id,
                content=text or None,
                tool_calls=tool_calls or None,
            )
            # Runs the tool calls (if any) and appends their results to the chat log.
            async for _ in chat_log.async_add_assistant_content(content):
                pass

            if not chat_log.unresponded_tool_results:
                break

        return conversation.async_get_result_from_chat_log(user_input, chat_log)
