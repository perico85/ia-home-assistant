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
        # HA 2024.11+ con nueva API
        from homeassistant.components.conversation import async_create_agent

        agent_entry = async_create_agent(hass, entry, agent)
        hass.data[DOMAIN][f"{entry.entry_id}_agent"] = agent_entry
        _LOGGER.info(f"IA Assistant registrado correctamente (nueva API) con URL: {addon_url}")
        return True

    except ImportError:
        try:
            # HA 2024.x con API anterior
            from homeassistant.components.conversation import async_register_agent

            async_register_agent(hass, DOMAIN, entry.entry_id, agent)
            hass.data[DOMAIN][f"{entry.entry_id}_agent"] = agent
            _LOGGER.info(f"IA Assistant registrado correctamente (API anterior) con URL: {addon_url}")
            return True

        except ImportError:
            try:
                # Fallback: guardar en hass.data
                from homeassistant.components.conversation import DOMAIN as CONVERSATION_DOMAIN
                hass.data.setdefault(CONVERSATION_DOMAIN, {})
                hass.data[CONVERSATION_DOMAIN][entry.entry_id] = agent
                _LOGGER.info(f"IA Assistant registrado correctamente (fallback) con URL: {addon_url}")
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
        # Eliminar agente
        agent_key = f"{entry.entry_id}_agent"
        if agent_key in hass.data[DOMAIN]:
            del hass.data[DOMAIN][agent_key]
        del hass.data[DOMAIN][entry.entry_id]
    return True