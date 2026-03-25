"""Constantes para la integración"""

DOMAIN = "ia_assistant"

# Configuración
CONF_LLM_PROVIDER = "llm_provider"
CONF_LLM_MODEL = "llm_model"
CONF_API_KEY = "api_key"
CONF_BASE_URL = "base_url"
CONF_HA_TOKEN = "ha_token"
CONF_SECURITY_MODE = "security_mode"
CONF_LANGUAGE = "language"

# Valores por defecto
DEFAULT_PROVIDER = "ollama"
DEFAULT_MODEL = "llama3.2"
DEFAULT_SECURITY_MODE = "hybrid"
DEFAULT_LANGUAGE = "es"

# Proveedores soportados
SUPPORTED_PROVIDERS = {
    "ollama": {
        "name": "Ollama (local/cloud)",
        "models": ["llama3.2", "llama3.1:70b", "mistral", "codellama", "gemma2"]
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    },
    "minimax": {
        "name": "MiniMax",
        "models": ["minimax-m2.7:cloud", "minimax-m1:cloud", "abab6.5-chat"]
    },
    "deepseek": {
        "name": "DeepSeek",
        "models": ["deepseek-chat", "deepseek-coder"]
    },
    "groq": {
        "name": "Groq",
        "models": ["llama-3.1-70b", "mixtral-8x7b"]
    }
}