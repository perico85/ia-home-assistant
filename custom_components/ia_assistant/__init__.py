"""IA Home Assistant - Integración para Home Assistant Assist"""

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_ADDON_URL, DEFAULT_ADDON_URL

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Set up IA Assistant from a config entry."""
    from .conversation_agent import IAConversationAgent

    agent = IAConversationAgent(hass, entry)
    async_add_entities([agent])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True