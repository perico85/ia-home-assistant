"""Constantes para IA Assistant"""

DOMAIN = "ia_assistant"

# Configuración
CONF_ADDON_URL = "addon_url"
CONF_LLM_PROVIDER = "llm_provider"
CONF_LLM_MODEL = "llm_model"
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_HA_TOKEN = "ha_token"
CONF_SECURITY_MODE = "security_mode"
CONF_LANGUAGE = "language"

# Valores por defecto
DEFAULT_PROVIDER = "ollama_cloud"
DEFAULT_MODEL = "llama3.2"
DEFAULT_SECURITY_MODE = "hybrid"
DEFAULT_LANGUAGE = "es"
DEFAULT_ADDON_URL = "http://homeassistant:8080"

# Proveedores soportados
SUPPORTED_PROVIDERS = {
    "ollama_cloud": {
        "name": "Ollama Cloud",
        "models": ["llama3.2", "llama3.1:70b", "minimax-m2.7:cloud", "gpt-oss:120b-cloud"]
    },
    "ollama_local": {
        "name": "Ollama Local",
        "models": ["llama3.2", "mistral", "codellama", "gemma2"]
    }
}