"""IA Home Assistant - Integración para Home Assistant Assist"""

import logging
from homeassistant.components.conversation import async_register

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL
from .conversation_agent import IAConversationAgent

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Configurar la integración"""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass, entry):
    """Configurar desde entrada de configuración"""
    # Guardar configuración
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Obtener URL del addon
    addon_url = entry.data.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)

    # Crear el agente de conversación
    agent = IAConversationAgent(hass, entry.data)

    # Registrar el agente de conversación
    try:
        # Usar la nueva API de registro
        from homeassistant.components.conversation import async_create_agent

        # Registrar en el registro de agentes
        hass.data[DOMAIN][f"{entry.entry_id}_agent"] = agent

        # Registrar para que aparezca en la lista de agentes
        async_register(hass, DOMAIN, entry.entry_id, agent)

        _LOGGER.info(f"IA Assistant registrado correctamente con URL: {addon_url}")
        return True

    except Exception as e:
        _LOGGER.error(f"Error registrando IA Assistant: {e}")
        return False


async def async_unload_entry(hass, entry):
    """Descargar entrada de configuración"""
    if entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]
    return True