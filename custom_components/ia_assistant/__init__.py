"""IA Home Assistant - Integración para Home Assistant Assist"""

from .const import DOMAIN
from .conversation_agent import IAConversationAgent

async def async_setup(hass, config):
    """Configurar la integración"""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass, entry):
    """Configurar desde entrada de configuración"""
    # Guardar configuración
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Registrar el agente de conversación
    from homeassistant.components.conversation import async_register

    agent = IAConversationAgent(hass, entry.data)
    async_register(hass, DOMAIN, entry.entry_id, agent)

    return True


async def async_unload_entry(hass, entry):
    """Descargar entrada de configuración"""
    if entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]
    return True