"""IA Home Assistant - Integración para Home Assistant Assist"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL
from .conversation_agent import IAConversationAgent

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Configurar la integración"""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar desde entrada de configuración"""
    # Guardar configuración
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "agent": None
    }

    # Obtener URL del addon
    addon_url = entry.data.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)

    # Crear el agente de conversación
    agent = IAConversationAgent(hass, entry.data)

    # Guardar referencia al agente
    hass.data[DOMAIN][entry.entry_id]["agent"] = agent

    _LOGGER.info(f"IA Assistant registrado con URL: {addon_url}")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar entrada de configuración"""
    if entry.entry_id in hass.data.get(DOMAIN, {}):
        del hass.data[DOMAIN][entry.entry_id]
    return True