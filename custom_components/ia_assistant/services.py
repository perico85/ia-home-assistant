"""Servicios disponibles para la integración"""

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

SERVICE_CHAT = "chat"
SERVICE_SET_MODEL = "set_model"
SERVICE_CLEAR_HISTORY = "clear_history"

CHAT_SCHEMA = vol.Schema({
    vol.Required("message"): str,
    vol.Optional("context"): dict,
})

SET_MODEL_SCHEMA = vol.Schema({
    vol.Required("model"): str,
})


async def async_setup_services(hass: HomeAssistant):
    """Configurar servicios"""

    async def handle_chat(call: ServiceCall):
        """Manejar servicio de chat"""
        message = call.data.get("message")
        context = call.data.get("context", {})

        # Obtener el agente
        agent = hass.data.get(DOMAIN, {}).get("agent")
        if not agent:
            return {"error": "Agente no inicializado"}

        # Procesar mensaje
        result = await agent.process_message(message, context)
        return result

    async def handle_set_model(call: ServiceCall):
        """Cambiar modelo"""
        model = call.data.get("model")

        agent = hass.data.get(DOMAIN, {}).get("agent")
        if not agent:
            return {"error": "Agente no inicializado"}

        agent.set_model(model)
        return {"success": True, "model": model}

    async def handle_clear_history(call: ServiceCall):
        """Limpiar historial"""
        agent = hass.data.get(DOMAIN, {}).get("agent")
        if agent:
            agent.clear_history()
        return {"success": True}

    hass.services.async_register(DOMAIN, SERVICE_CHAT, handle_chat, schema=CHAT_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_SET_MODEL, handle_set_model, schema=SET_MODEL_SCHEMA)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_HISTORY, handle_clear_history)