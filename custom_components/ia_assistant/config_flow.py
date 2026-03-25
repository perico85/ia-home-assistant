"""Configuración de la integración IA Home Assistant"""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_ADDON_URL,
    CONF_LLM_MODEL,
    CONF_SECURITY_MODE,
    CONF_LANGUAGE,
    DEFAULT_ADDON_URL,
    DEFAULT_MODEL,
    DEFAULT_SECURITY_MODE,
    DEFAULT_LANGUAGE,
)


class IAAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para IA Assistant"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Paso inicial de configuración"""
        errors = {}

        if user_input is not None:
            # Verificar conexión con el addon
            addon_url = user_input.get(CONF_ADDON_URL, DEFAULT_ADDON_URL)
            if await self._test_addon_connection(addon_url):
                return self.async_create_entry(
                    title=f"IA Assistant ({user_input.get(CONF_LLM_MODEL, DEFAULT_MODEL)})",
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        # Mostrar formulario
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Optional(CONF_ADDON_URL, default=DEFAULT_ADDON_URL): str,
                vol.Optional(CONF_LLM_MODEL, default=DEFAULT_MODEL): str,
                vol.Optional(CONF_SECURITY_MODE, default=DEFAULT_SECURITY_MODE): vol.In(
                    ["safe", "hybrid", "unrestricted"]
                ),
                vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                    ["es", "en", "de", "fr", "it", "pt"]
                ),
            }),
            errors=errors,
        )

    async def _test_addon_connection(self, url: str) -> bool:
        """Verificar conexión con el addon"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def async_step_onboarding(self, data=None):
        """Configuración automática desde el addon"""
        if data is None:
            data = {
                CONF_ADDON_URL: DEFAULT_ADDON_URL,
                CONF_LLM_MODEL: DEFAULT_MODEL,
                CONF_SECURITY_MODE: DEFAULT_SECURITY_MODE,
                CONF_LANGUAGE: DEFAULT_LANGUAGE,
            }
        return self.async_create_entry(title="IA Assistant", data=data)