"""
Agente de conversación para Home Assistant Assist
Compatible con Home Assistant 2026+
"""

import logging
import aiohttp
from typing import Optional, List, Dict, Any
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import ulid

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL

_LOGGER = logging.getLogger(__name__)

# Importaciones condicionales para compatibilidad
try:
    # HA 2024.11+ usa la nueva API
    from homeassistant.components.conversation import (
        AbstractConversationAgent,
        ConversationInput,
        ConversationResult,
        ConversationOutput,
    )
    NEW_API = True
except ImportError:
    # Versiones anteriores
    try:
        from homeassistant.components.conversation import (
            ConversationAgent,
            ConversationInput,
            ConversationResult,
        )
        AbstractConversationAgent = ConversationAgent
        ConversationOutput = None
        NEW_API = False
    except ImportError:
        AbstractConversationAgent = None
        ConversationInput = None
        ConversationResult = None
        ConversationOutput = None
        NEW_API = False


class IAConversationAgent:
    """
    Agente de conversación que se comunica con el addon IA Home Assistant
    """

    def __init__(self, hass: HomeAssistant, config: dict):
        """Inicializar el agente"""
        self.hass = hass
        self.config = config
        self._addon_url = config.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)
        self._language = config.get("language", "es")

    @property
    def attribution(self):
        """Atribución del agente"""
        return {
            "name": "IA Home Assistant",
            "url": "https://github.com/perico85/ia-home-assistant",
        }

    @property
    def default_speech(self) -> str:
        """Mensaje por defecto cuando no se entiende"""
        return {
            "es": "No he entendido tu solicitud. ¿Puedes reformularla?",
            "en": "I didn't understand your request. Can you rephrase?",
        }.get(self._language, "I didn't understand.")

    @property
    def supported_languages(self) -> List[str]:
        """Idiomas soportados"""
        return ["es", "en", "de", "fr", "it", "pt"]

    async def async_process(
        self,
        hass: HomeAssistant,
        user_input: str,
        conversation_id: Optional[str] = None,
        language: Optional[str] = None,
        agent_id: Optional[str] = None,
        device_id: Optional[str] = None,
        extra_exposed_entities: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Procesar entrada de conversación enviando al addon via API
        """
        language = language or self._language

        _LOGGER.debug(f"Procesando: '{user_input}' (idioma: {language})")

        try:
            # Obtener entidades expuestas para contexto
            exposed_entities = await self._get_exposed_entities(hass)

            # Llamar a la API del addon
            response = await self._call_addon_api(
                user_input,
                language,
                exposed_entities,
                conversation_id
            )

            if response.get("success"):
                message = response.get("message", self.default_speech)
                return {"response": message, "conversation_id": conversation_id or ulid.ulid()}
            else:
                error = response.get("error", "Error desconocido")
                return {"response": f"Error: {error}", "conversation_id": conversation_id or ulid.ulid()}

        except Exception as e:
            _LOGGER.error(f"Error procesando conversación: {e}")
            return {"response": f"Error de conexión con el addon: {str(e)}", "conversation_id": conversation_id or ulid.ulid()}

    async def _call_addon_api(
        self,
        text: str,
        language: str,
        entities: List[Dict],
        conversation_id: Optional[str] = None
    ) -> Dict:
        """Llamar a la API del addon"""
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

    async def _get_exposed_entities(self, hass: HomeAssistant) -> List[Dict]:
        """Obtener entidades expuestas al asistente"""
        try:
            from homeassistant.components.homeassistant.exposed_entities import async_should_expose

            states = hass.states.async_all()
            exposed = []

            for state in states:
                if async_should_expose(hass, "conversation", state.entity_id):
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