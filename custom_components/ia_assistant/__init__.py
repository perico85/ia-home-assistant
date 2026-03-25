"""IA Home Assistant - Integración para Home Assistant Assist"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL
from .conversation_agent import IAConversationAgent

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Configurar la integración"""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar desde entrada de configuración"""
    # Guardar configuración
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Obtener URL del addon
    addon_url = entry.data.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)

    # Crear el agente de conversación
    agent = IAConversationAgent(hass, entry.data)

    # Registrar el agente de conversación
    try:
        from homeassistant.components.conversation import async_set_agent

        async_set_agent(hass, entry, agent)
        _LOGGER.info(f"IA Assistant registrado correctamente con URL: {addon_url}")
        return True

    except ImportError:
        # Fallback para versiones anteriores
        try:
            from homeassistant.components.conversation import DOMAIN as CONVERSATION_DOMAIN
            hass.data.setdefault(CONVERSATION_DOMAIN, {})
            hass.data[CONVERSATION_DOMAIN][entry.entry_id] = agent
            _LOGGER.info(f"IA Assistant registrado (método fallback) con URL: {addon_url}")
            return True
        except Exception as e:
            _LOGGER.error(f"Error registrando IA Assistant: {e}")
            return False
    except Exception as e:
        _LOGGER.error(f"Error registrando IA Assistant: {e}")
        return False


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar entrada de configuración"""
    if entry.entry_id in hass.data[DOMAIN]:
        del hass.data[DOMAIN][entry.entry_id]
    return True