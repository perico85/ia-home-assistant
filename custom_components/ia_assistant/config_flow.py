"""Configuración de la integración"""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv

from .const import (
    DOMAIN,
    CONF_LLM_PROVIDER,
    CONF_LLM_MODEL,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_SECURITY_MODE,
    CONF_LANGUAGE,
    DEFAULT_PROVIDER,
    DEFAULT_MODEL,
    DEFAULT_SECURITY_MODE,
    DEFAULT_LANGUAGE,
    SUPPORTED_PROVIDERS,
)


class IAAssistantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para IA Assistant"""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Paso inicial de configuración"""
        errors = {}

        if user_input is not None:
            # Validar entrada
            if user_input.get(CONF_API_KEY) or user_input.get(CONF_LLM_PROVIDER) == "ollama":
                # Crear entrada
                return self.async_create_entry(
                    title=f"IA Assistant ({user_input[CONF_LLM_MODEL]})",
                    data=user_input
                )
            else:
                errors["base"] = "api_key_required"

        # Mostrar formulario
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_LLM_PROVIDER, default=DEFAULT_PROVIDER): vol.In(
                    {k: v["name"] for k, v in SUPPORTED_PROVIDERS.items()}
                ),
                vol.Required(CONF_LLM_MODEL, default=DEFAULT_MODEL): str,
                vol.Optional(CONF_API_KEY): str,
                vol.Optional(CONF_BASE_URL): str,
                vol.Optional(CONF_SECURITY_MODE, default=DEFAULT_SECURITY_MODE): vol.In(
                    ["safe", "hybrid", "unrestricted"]
                ),
                vol.Optional(CONF_LANGUAGE, default=DEFAULT_LANGUAGE): vol.In(
                    ["es", "en", "de", "fr", "it", "pt"]
                ),
            }),
            errors=errors,
        )

    async def async_step_import(self, import_config):
        """Importar configuración desde YAML"""
        return await self.async_step_user(import_config)