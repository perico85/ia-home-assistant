"""
Agente de conversación para Home Assistant Assist
Integra el asistente IA con el sistema nativo de Home Assistant
"""

import logging
import json
from typing import Optional, List, Dict, Any
from homeassistant.components.conversation import (
    ConversationAgent,
    ConversationInput,
    ConversationResult,
    ConversationSlot,
    IntentResponse,
)
from homeassistant.components.homeassistant.exposed_entities import async_should_expose
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import intent
from homeassistant.util import ulid

from .const import DOMAIN, CONF_LLM_PROVIDER, CONF_LLM_MODEL, CONF_API_KEY

_LOGGER = logging.getLogger(__name__)


class IAConversationAgent(ConversationAgent):
    """
    Agente de conversación que usa el LLM seleccionado
    para procesar comandos de voz/texto en Home Assistant
    """

    def __init__(self, hass: HomeAssistant, config: dict):
        """Inicializar el agente"""
        self.hass = hass
        self.config = config
        self._llm_client = None
        self._ha_client = None
        self._context = []

        # Configuración
        self.provider = config.get(CONF_LLM_PROVIDER, "ollama")
        self.model = config.get(CONF_LLM_MODEL, "llama3.2")
        self.api_key = config.get(CONF_API_KEY, "")
        self.language = config.get("language", "es")
        self.security_mode = config.get("security_mode", "hybrid")

    @property
    def attribution(self):
        """Atribución del agente"""
        return {
            "name": "IA Home Assistant",
            "url": "https://github.com/tu-usuario/ia-home-assistant",
        }

    @property
    def default_speech(self):
        """Mensaje por defecto cuando no se entiende"""
        return {
            "es": "No he entendido tu solicitud. ¿Puedes reformularla?",
            "en": "I didn't understand your request. Can you rephrase?",
        }.get(self.language, "I didn't understand.")

    async def async_initialize(self):
        """Inicializar conexiones"""
        from ..app.core.llm_client import create_llm_client
        from ..app.core.ha_api import HomeAssistantClient

        # Crear cliente LLM
        self._llm_client = create_llm_client(
            model=self.model,
            provider=self.provider,
            api_key=self.api_key
        )

        # El cliente de HA usa la API interna
        self._ha_client = None  # Usaremos la API de HA directamente

        _LOGGER.info(f"IA Conversation Agent inicializado con modelo {self.model}")

    async def async_process(
        self,
        hass: HomeAssistant,
        conversation_input: ConversationInput,
        context: Optional[Dict[str, Any]] = None
    ) -> ConversationResult:
        """
        Procesar entrada de conversación

        Este es el método principal que Home Assistant llama cuando
        recibe un comando de voz o texto.
        """
        # Inicializar si es necesario
        if self._llm_client is None:
            await self.async_initialize()

        # Obtener texto del usuario
        user_input = conversation_input.text
        language = conversation_input.language or self.language

        _LOGGER.debug(f"Procesando: '{user_input}' (idioma: {language})")

        try:
            # Construir contexto del sistema
            system_prompt = await self._build_system_prompt(language)

            # Obtener entidades expuestas
            exposed_entities = await self._get_exposed_entities(hass)

            # Construir mensajes para el LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]

            # Añadir contexto de conversación previa
            if self._context:
                messages.insert(1, {"role": "user", "content": self._context[-1].get("user", "")})
                messages.insert(2, {"role": "assistant", "content": self._context[-1].get("assistant", "")})

            # Preparar herramientas (function calling)
            tools = self._get_tools(exposed_entities)

            # Llamar al LLM
            response = await self._llm_client.chat(messages, tools)

            if not response.get("success"):
                return self._create_error_result(
                    f"Error del modelo: {response.get('error', 'Desconocido')}"
                )

            # Procesar respuesta
            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls")

            # Si hay llamadas a herramientas, ejecutarlas
            if tool_calls:
                result = await self._execute_tool_calls(hass, tool_calls)
                return self._create_success_result(result.get("message", content))

            # Actualizar contexto
            self._context.append({
                "user": user_input,
                "assistant": content
            })
            if len(self._context) > 10:
                self._context.pop(0)

            return self._create_success_result(content)

        except Exception as e:
            _LOGGER.error(f"Error procesando conversación: {e}")
            return self._create_error_result(f"Error: {str(e)}")

    async def _build_system_prompt(self, language: str) -> str:
        """Construir prompt del sistema con contexto de HA"""
        # Obtener entidades y estados
        states = self.hass.states.async_all()

        # Filtrar entidades relevantes
        relevant_entities = [
            state for state in states
            if async_should_expose(self.hass, "conversation", state.entity_id)
        ]

        # Construir resumen de entidades
        entity_summary = []
        for state in relevant_entities[:50]:  # Limitar a 50
            entity_id = state.entity_id
            friendly_name = state.attributes.get("friendly_name", entity_id)
            entity_summary.append(f"- {friendly_name} ({entity_id}): {state.state}")

        entities_text = "\n".join(entity_summary) if entity_summary else "No hay entidades expuestas."

        # Prompt del sistema
        prompts = {
            "es": f"""Eres un asistente inteligente para Home Assistant.

Tu objetivo es ayudar a controlar la casa mediante comandos naturales.

Entidades disponibles:
{entities_text}

Capacidades:
- Encender/apagar luces, interruptores y otros dispositivos
- Consultar estados y valores de sensores
- Controlar clima (termostatos, aires acondicionados)
- Reproducir medios
- Ejecutar automatizaciones y scripts

Reglas:
1. Responde siempre en español
2. Sé conciso pero útil
3. Si necesitas clarificar, pregunta brevemente
4. Para acciones críticas, confirma con el usuario
5. Usa las herramientas disponibles para interactuar con Home Assistant

Cuando quieras ejecutar una acción, usa las herramientas disponibles.""",

            "en": f"""You are an intelligent assistant for Home Assistant.

Your goal is to help control the home through natural commands.

Available entities:
{entities_text}

Capabilities:
- Turn on/off lights, switches and other devices
- Query states and values from sensors
- Control climate (thermostats, air conditioners)
- Play media
- Execute automations and scripts

Rules:
1. Always respond in English
2. Be concise but helpful
3. If you need to clarify, ask briefly
4. For critical actions, confirm with the user
5. Use the available tools to interact with Home Assistant

When you want to execute an action, use the available tools."""
        }

        return prompts.get(language, prompts["en"])

    async def _get_exposed_entities(self, hass: HomeAssistant) -> List[Dict]:
        """Obtener entidades expuestas al asistente"""
        states = hass.states.async_all()
        exposed = []

        for state in states:
            if async_should_expose(hass, "conversation", state.entity_id):
                exposed.append({
                    "entity_id": state.entity_id,
                    "state": state.state,
                    "attributes": dict(state.attributes)
                })

        return exposed

    def _get_tools(self, entities: List[Dict]) -> List[Dict]:
        """Definir herramientas disponibles para el LLM"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "turn_on",
                    "description": "Encender una entidad (luz, interruptor, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad a encender"
                            }
                        },
                        "required": ["entity_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "turn_off",
                    "description": "Apagar una entidad (luz, interruptor, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad a apagar"
                            }
                        },
                        "required": ["entity_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_state",
                    "description": "Obtener el estado de una entidad",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad"
                            }
                        },
                        "required": ["entity_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_value",
                    "description": "Establecer un valor en una entidad (brillo, temperatura, etc.)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad"
                            },
                            "value": {
                                "type": "number",
                                "description": "Valor a establecer"
                            }
                        },
                        "required": ["entity_id", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "call_service",
                    "description": "Llamar a un servicio de Home Assistant",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "domain": {
                                "type": "string",
                                "description": "Dominio (light, switch, climate, etc.)"
                            },
                            "service": {
                                "type": "string",
                                "description": "Nombre del servicio (turn_on, turn_off, etc.)"
                            },
                            "entity_id": {
                                "type": "string",
                                "description": "ID de la entidad objetivo"
                            },
                            "data": {
                                "type": "object",
                                "description": "Datos adicionales del servicio"
                            }
                        },
                        "required": ["domain", "service"]
                    }
                }
            }
        ]

    async def _execute_tool_calls(self, hass: HomeAssistant, tool_calls: List[Dict]) -> Dict:
        """Ejecutar llamadas a herramientas"""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.get("function", {}).get("name")
            arguments = json.loads(tool_call.get("function", {}).get("arguments", "{}"))

            try:
                result = await self._execute_single_tool(hass, function_name, arguments)
                results.append({"name": function_name, "result": result})
            except Exception as e:
                _LOGGER.error(f"Error ejecutando {function_name}: {e}")
                results.append({"name": function_name, "error": str(e)})

        # Generar mensaje de respuesta
        success_count = sum(1 for r in results if "result" in r)
        if success_count == len(results):
            message = f"Acción ejecutada correctamente. ({success_count} acciones)"
        else:
            message = f"Se completaron {success_count} de {len(results)} acciones."

        return {"success": success_count == len(results), "message": message, "results": results}

    async def _execute_single_tool(self, hass: HomeAssistant, name: str, arguments: Dict) -> Dict:
        """Ejecutar una herramienta específica"""
        entity_id = arguments.get("entity_id")

        if name == "turn_on":
            domain = entity_id.split(".")[0] if entity_id else "light"
            await hass.services.async_call(domain, "turn_on", {"entity_id": entity_id})
            return {"success": True, "message": f"Encendido {entity_id}"}

        elif name == "turn_off":
            domain = entity_id.split(".")[0] if entity_id else "light"
            await hass.services.async_call(domain, "turn_off", {"entity_id": entity_id})
            return {"success": True, "message": f"Apagado {entity_id}"}

        elif name == "get_state":
            state = hass.states.get(entity_id)
            if state:
                return {
                    "success": True,
                    "entity_id": entity_id,
                    "state": state.state,
                    "attributes": dict(state.attributes)
                }
            return {"success": False, "error": f"Entidad no encontrada: {entity_id}"}

        elif name == "set_value":
            domain = entity_id.split(".")[0] if entity_id else "light"
            value = arguments.get("value")
            if domain == "light":
                await hass.services.async_call("light", "turn_on", {
                    "entity_id": entity_id,
                    "brightness": value
                })
            elif domain == "climate":
                await hass.services.async_call("climate", "set_temperature", {
                    "entity_id": entity_id,
                    "temperature": value
                })
            return {"success": True, "message": f"Valor establecido a {value}"}

        elif name == "call_service":
            domain = arguments.get("domain")
            service = arguments.get("service")
            data = arguments.get("data", {})
            if entity_id:
                data["entity_id"] = entity_id
            await hass.services.async_call(domain, service, data)
            return {"success": True, "message": f"Servicio {domain}.{service} ejecutado"}

        return {"success": False, "error": f"Herramienta desconocida: {name}"}

    def _create_success_result(self, message: str) -> ConversationResult:
        """Crear resultado exitoso"""
        intent_response = intent.IntentResponse(language=self.language)
        intent_response.async_set_speech(message)
        return ConversationResult(
            response=intent_response,
            conversation_id=ulid.ulid(),
        )

    def _create_error_result(self, error: str) -> ConversationResult:
        """Crear resultado de error"""
        intent_response = intent.IntentResponse(language=self.language)
        intent_response.async_set_speech(f"Error: {error}")
        return ConversationResult(
            response=intent_response,
            conversation_id=ulid.ulid(),
        )