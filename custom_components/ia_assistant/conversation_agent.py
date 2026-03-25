"""
Agente de conversación para Home Assistant Assist
Compatible con Home Assistant 2024.11+
"""

from __future__ import annotations

import logging
import aiohttp
from typing import List

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL

_LOGGER = logging.getLogger(__name__)


class IAConversationAgent(conversation.ConversationEntity, conversation.AbstractConversationAgent):
    """Agente de conversación IA para Home Assistant."""

    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.entry = entry
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id
        self._attr_supported_features = conversation.ConversationEntityFeature.CONTROL
        self._addon_url = entry.data.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)
        self._language = entry.data.get("language", "es")

    @property
    def supported_languages(self) -> List[str]:
        """Return a list of supported languages."""
        return ["es", "en", "de", "fr", "it", "pt"]

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        text = user_input.text
        language = user_input.language or self._language
        conversation_id = user_input.conversation_id or ulid.ulid()

        _LOGGER.debug(f"Procesando: '{text}' (idioma: {language})")

        try:
            # Obtener entidades expuestas para contexto
            exposed_entities = await self._get_exposed_entities()

            # Llamar a la API del addon
            response = await self._call_addon_api(
                text,
                language,
                exposed_entities,
                conversation_id
            )

            if response.get("success"):
                message = response.get("message", self._default_speech)
                return self._create_success_result(message, conversation_id)
            else:
                error = response.get("error", "Error desconocido")
                return self._create_error_result(f"Error: {error}", conversation_id)

        except Exception as e:
            _LOGGER.error(f"Error procesando conversación: {e}")
            return self._create_error_result(f"Error de conexión: {str(e)}", conversation_id)

    @property
    def _default_speech(self) -> str:
        """Default speech when not understood."""
        return {
            "es": "No he entendido tu solicitud. ¿Puedes reformularla?",
            "en": "I didn't understand your request. Can you rephrase?",
        }.get(self._language, "I didn't understand.")

    async def _call_addon_api(
        self, text: str, language: str, entities: list, conversation_id: str
    ) -> dict:
        """Call the addon API."""
        url = f"{self._addon_url}/api/chat"

        payload = {
            "message": text,
            "language": language,
            "context": {
                "entities": entities[:50],
                "conversation_id": conversation_id
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        _LOGGER.error(f"Error del addon ({response.status}): {error_text}")
                        return {"success": False, "error": f"HTTP {response.status}"}
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Error conectando al addon: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            _LOGGER.error(f"Excepción llamando al addon: {e}")
            return {"success": False, "error": str(e)}

    async def _get_exposed_entities(self) -> list:
        """Get exposed entities for context."""
        try:
            from homeassistant.components.homeassistant.exposed_entities import async_should_expose

            states = self.hass.states.async_all()
            exposed = []

            for state in states:
                if async_should_expose(self.hass, "conversation", state.entity_id):
                    exposed.append({
                        "entity_id": state.entity_id,
                        "state": state.state,
                        "attributes": {
                            "friendly_name": state.attributes.get("friendly_name", state.entity_id),
                            "device_class": state.attributes.get("device_class"),
                            "unit_of_measurement": state.attributes.get("unit_of_measurement"),
                        }
                    })

            return exposed
        except Exception as e:
            _LOGGER.warning(f"Error obteniendo entidades expuestas: {e}")
            return []

    def _create_success_result(self, message: str, conversation_id: str) -> conversation.ConversationResult:
        """Create a successful result."""
        intent_response = intent.IntentResponse(language=self._language)
        intent_response.async_set_speech(message)
        return conversation.ConversationResult(
            conversation_id=conversation_id,
            response=intent_response
        )

    def _create_error_result(self, error: str, conversation_id: str) -> conversation.ConversationResult:
        """Create an error result."""
        intent_response = intent.IntentResponse(language=self._language)
        intent_response.async_set_error(intent.IntentResponseErrorCode.NO_INTENT_MATCH, error)
        return conversation.ConversationResult(
            conversation_id=conversation_id,
            response=intent_response
        )