"""
Conversation Agent para Home Assistant Assist
Permite usar el IA Assistant como asistente de voz nativo
"""

import logging
from typing import Optional

from homeassistant.components.conversation import (
    AbstractConversationAgent,
    ConversationInput,
    ConversationResult,
    ConversationSpan,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IAConversationAgent(AbstractConversationAgent):
    """
    Agente de conversación que conecta con el backend IA Assistant
    Permite usar el asistente a través de Assist de Home Assistant
    """

    def __init__(self, hass: HomeAssistant, entry):
        """Inicializar el agente de conversación"""
        self.hass = hass
        self.entry = entry
        self.client = None

    @property
    def supported_languages(self) -> list[str]:
        """Idiomas soportados"""
        return ["es", "en", "de", "fr", "it", "pt", "ca", "gl"]

    async def async_initialize(self, hass: HomeAssistant):
        """Inicializar el agente"""
        self.client = hass.data.get(DOMAIN, {}).get("client")
        _LOGGER.info("IA Conversation Agent inicializado")

    async def async_process(
        self,
        hass: HomeAssistant,
        conversation_input: ConversationInput,
        conversation_span: Optional[ConversationSpan] = None
    ) -> ConversationResult:
        """
        Procesar entrada de conversación

        Args:
            hass: Instancia de Home Assistant
            conversation_input: Entrada del usuario (texto o voz)
            conversation_span: Span de conversación (opcional)

        Returns:
            ConversationResult con la respuesta
        """
        # Obtener cliente
        if not self.client:
            self.client = hass.data.get(DOMAIN, {}).get("client")

        if not self.client:
            _LOGGER.error("Cliente IA no inicializado")
            return ConversationResult(
                response=intent.IntentResponse(
                    intent=intent.Intent(intent.INTENT_UNKNOWN)
                ),
                conversation_id=conversation_input.conversation_id or ulid.ulid()
            )

        # Obtener mensaje del usuario
        user_message = conversation_input.text
        language = hass.config.language or "es"

        _LOGGER.info(f"Procesando mensaje: {user_message}")

        # Obtener contexto de dispositivos
        context = await self._build_device_context(hass)

        # Enviar al backend IA
        response = await self.client.chat(
            message=user_message,
            language=language,
            context=context
        )

        if not response.get("success", False):
            _LOGGER.error(f"Error del backend: {response.get('error')}")
            return ConversationResult(
                response=self._create_error_response(
                    "Lo siento, hubo un error al procesar tu solicitud.",
                    language
                ),
                conversation_id=conversation_input.conversation_id or ulid.ulid()
            )

        # Obtener respuesta del asistente
        assistant_message = response.get("message", {}).get("content", "")
        if not assistant_message:
            assistant_message = response.get("response", "No pude procesar la solicitud.")

        _LOGGER.info(f"Respuesta: {assistant_message}")

        # Crear respuesta
        intent_response = intent.IntentResponse(language=language)
        intent_response.async_set_speech(assistant_message)

        # Si hay acciones ejecutadas, incluir en la respuesta
        actions = response.get("actions_executed", [])
        if actions:
            action_text = self._format_actions(actions)
            intent_response.async_set_speech(f"{assistant_message}\n\n{action_text}")

        return ConversationResult(
            response=intent_response,
            conversation_id=response.get("conversation_id", conversation_input.conversation_id)
        )

    async def _build_device_context(self, hass: HomeAssistant) -> dict:
        """
        Construir contexto con estado de dispositivos

        Args:
            hass: Instancia de Home Assistant

        Returns:
            Diccionario con contexto de dispositivos
        """
        context = {
            "devices": [],
            "areas": [],
            "current_states": {}
        }

        try:
            # Obtener estados de entidades
            states = hass.states.async_all()

            # Filtrar entidades relevantes
            relevant_domains = [
                "light", "switch", "climate", "cover", "media_player",
                "sensor", "binary_sensor", "input_boolean", "input_select"
            ]

            for state in states:
                entity_id = state.entity_id
                domain = entity_id.split(".")[0]

                if domain in relevant_domains:
                    context["current_states"][entity_id] = {
                        "state": state.state,
                        "attributes": dict(state.attributes)
                    }

                    # Añadir dispositivo resumido
                    device_info = {
                        "entity_id": entity_id,
                        "name": state.attributes.get("friendly_name", entity_id),
                        "domain": domain,
                        "state": state.state
                    }

                    # Añadir área si está disponible
                    if "area_id" in state.attributes:
                        device_info["area"] = state.attributes["area_id"]

                    context["devices"].append(device_info)

            # Obtener áreas
            area_registry = hass.helpers.area_registry.async_get(hass)
            areas = area_registry.async_list_areas()
            context["areas"] = [
                {"id": area.id, "name": area.name}
                for area in areas
            ]

        except Exception as e:
            _LOGGER.error(f"Error construyendo contexto: {e}")

        return context

    def _create_error_response(self, message: str, language: str) -> intent.IntentResponse:
        """Crear respuesta de error"""
        response = intent.IntentResponse(language=language)
        response.async_set_speech(message)
        return response

    def _format_actions(self, actions: list) -> str:
        """Formatear acciones ejecutadas"""
        if not actions:
            return ""

        formatted = []
        for action in actions:
            name = action.get("name", "Acción")
            entity = action.get("entity_id", "")
            success = "✓" if action.get("success") else "✗"
            formatted.append(f"{success} {name}: {entity}")

        return "Acciones ejecutadas:\n" + "\n".join(formatted)


async def async_register_agent(hass: HomeAssistant, entry):
    """Registrar el agente de conversación"""
    agent = IAConversationAgent(hass, entry)
    await agent.async_initialize(hass)

    # Registrar en el componente de conversación
    hass.data[DOMAIN]["agent"] = agent

    return agent