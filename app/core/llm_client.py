"""
Cliente LLM Unificado - Soporta múltiples proveedores
Ollama, OpenAI-compatible, MiniMax, y otros clouds
"""

import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseLLMClient(ABC):
    """Clase base para clientes LLM"""

    @abstractmethod
    async def chat(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """Enviar mensaje de chat"""
        pass

    @abstractmethod
    async def chat_stream(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> AsyncIterator[str]:
        """Chat con streaming"""
        pass

    @abstractmethod
    def set_model(self, model: str) -> None:
        """Cambiar modelo"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Verificar conexión"""
        pass


class OllamaClient(BaseLLMClient):
    """Cliente para Ollama (local y cloud)"""

    PROVIDERS = {
        "ollama": "http://localhost:11434",
        "ollama_cloud": "https://api.ollama.ai",
    }

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        api_key: str = "",
        model: str = "llama3.2"
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def set_model(self, model: str) -> None:
        """Cambiar el modelo dinámicamente"""
        self.model = model
        logger.info(f"Modelo cambiado a: {model}")

    def test_connection(self) -> bool:
        """Verificar conexión"""
        import requests
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Enviar mensaje de chat"""
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": stream}
        if tools:
            payload["tools"] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=self.headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {"success": True, "message": data.get("message", {}), "model": self.model}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API Error: {response.status}", "details": error_text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """Chat con streaming"""
        url = f"{self.base_url}/api/chat"
        payload = {"model": self.model, "messages": messages, "stream": True}
        if tools:
            payload["tools"] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=self.headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                try:
                                    data = json.loads(line.decode('utf-8'))
                                    if 'message' in data:
                                        content = data['message'].get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
        except Exception as e:
            yield f"[Error: {e}]"


class OpenAICompatibleClient(BaseLLMClient):
    """
    Cliente para APIs compatibles con OpenAI
    Soporta: OpenAI, MiniMax, DeepSeek, Groq, y otros
    """

    # Proveedores conocidos con sus endpoints
    KNOWN_PROVIDERS = {
        "openai": "https://api.openai.com/v1",
        "minimax": "https://api.minimax.chat/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "groq": "https://api.groq.com/openai/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "together": "https://api.together.xyz/v1",
    }

    # Mapeo de modelos a proveedores
    MODEL_PROVIDERS = {
        "gpt-4": "openai",
        "gpt-3.5": "openai",
        "minimax-m2": "minimax",
        "minimax-m1": "minimax",
        "abab": "minimax",
        "deepseek": "deepseek",
        "llama": "groq",
        "mixtral": "groq",
    }

    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "gpt-4o-mini",
        provider: str = ""
    ):
        self.api_key = api_key
        self.model = model

        # Detectar proveedor automáticamente si no se especifica
        if not base_url:
            if provider and provider in self.KNOWN_PROVIDERS:
                self.base_url = self.KNOWN_PROVIDERS[provider]
            else:
                # Detectar por nombre de modelo
                detected_provider = self._detect_provider(model)
                self.base_url = self.KNOWN_PROVIDERS.get(detected_provider, "https://api.openai.com/v1")
        else:
            self.base_url = base_url.rstrip('/')

        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def _detect_provider(self, model: str) -> str:
        """Detectar proveedor basado en el nombre del modelo"""
        model_lower = model.lower()
        for key, provider in self.MODEL_PROVIDERS.items():
            if key in model_lower:
                return provider
        return "openai"  # Default

    def set_model(self, model: str) -> None:
        """Cambiar el modelo dinámicamente"""
        self.model = model
        # Re-detectar proveedor si es necesario
        detected = self._detect_provider(model)
        if detected in self.KNOWN_PROVIDERS:
            self.base_url = self.KNOWN_PROVIDERS[detected]
        logger.info(f"Modelo cambiado a: {model} (proveedor: {detected})")

    def test_connection(self) -> bool:
        """Verificar conexión"""
        import requests
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Enviar mensaje de chat (formato OpenAI)"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }

        # Añadir tools si están disponibles
        if tools:
            payload["tools"] = self._convert_tools(tools)
            payload["tool_choice"] = "auto"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=self.headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        choices = data.get("choices", [])
                        if choices:
                            message = choices[0].get("message", {})
                            return {
                                "success": True,
                                "message": message,
                                "model": self.model,
                                "tool_calls": message.get("tool_calls")
                            }
                        return {"success": False, "error": "No response"}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API Error: {response.status}", "details": error_text}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """Chat con streaming (formato OpenAI)"""
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = self._convert_tools(tools)
            payload["tool_choice"] = "auto"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=self.headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        async for line in response.content:
                            if line:
                                line_str = line.decode('utf-8').strip()
                                if line_str.startswith("data: "):
                                    data_str = line_str[6:]
                                    if data_str == "[DONE]":
                                        break
                                    try:
                                        data = json.loads(data_str)
                                        choices = data.get("choices", [])
                                        if choices:
                                            delta = choices[0].get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                yield content
                                    except json.JSONDecodeError:
                                        continue
        except Exception as e:
            yield f"[Error: {e}]"

    def _convert_tools(self, ollama_tools: List[Dict]) -> List[Dict]:
        """Convertir formato de tools de Ollama a OpenAI"""
        openai_tools = []
        for tool in ollama_tools:
            if tool.get("type") == "function":
                openai_tools.append(tool)
            else:
                # Convertir de formato Ollama a OpenAI
                openai_tools.append({
                    "type": "function",
                    "function": tool.get("function", tool)
                })
        return openai_tools


class UnifiedLLMClient:
    """
    Cliente unificado que detecta automáticamente el proveedor
    y usa el cliente apropiado
    """

    # Modelos que usan Ollama
    OLLAMA_MODELS = ["llama", "mistral", "gemma", "codellama", "deepseek-coder", "phi", "qwen"]

    # Modelos que usan OpenAI-compatible API
    OPENAI_COMPATIBLE_MODELS = ["gpt", "minimax", "claude", "deepseek-chat"]

    def __init__(
        self,
        provider: str = "auto",
        base_url: str = "",
        api_key: str = "",
        model: str = "llama3.2"
    ):
        self.provider = provider
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Inicializar el cliente apropiado"""
        if self.provider == "ollama" or self._is_ollama_model(self.model):
            self._client = OllamaClient(
                base_url=self.base_url or "http://localhost:11434",
                api_key=self.api_key,
                model=self.model
            )
            self._provider_type = "ollama"
        else:
            self._client = OpenAICompatibleClient(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model,
                provider=self.provider if self.provider != "auto" else ""
            )
            self._provider_type = "openai_compatible"

    def _is_ollama_model(self, model: str) -> bool:
        """Determinar si un modelo es de Ollama"""
        model_lower = model.lower()
        return any(m in model_lower for m in self.OLLAMA_MODELS)

    def set_model(self, model: str) -> None:
        """Cambiar modelo (puede cambiar de proveedor)"""
        self.model = model

        # Verificar si necesitamos cambiar de cliente
        new_is_ollama = self._is_ollama_model(model)
        current_is_ollama = self._provider_type == "ollama"

        if new_is_ollama != current_is_ollama:
            # Cambiar de cliente
            self._initialize_client()
        else:
            self._client.set_model(model)

        logger.info(f"Modelo cambiado a: {model} (tipo: {self._provider_type})")

    def test_connection(self) -> bool:
        """Verificar conexión"""
        return self._client.test_connection()

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Enviar mensaje de chat"""
        return await self._client.chat(messages, tools, stream)

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """Chat con streaming"""
        async for chunk in self._client.chat_stream(messages, tools):
            yield chunk

    @property
    def provider_type(self) -> str:
        """Tipo de proveedor actual"""
        return self._provider_type

    def get_available_models(self) -> List[str]:
        """Obtener modelos populares según el proveedor"""
        if self._provider_type == "ollama":
            return [
                "llama3.2", "llama3.1:70b", "mistral", "codellama",
                "gemma2", "deepseek-coder", "phi3"
            ]
        else:
            return [
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo",
                "minimax-m2.7:cloud", "minimax-m1:cloud",
                "deepseek-chat", "deepseek-coder",
                "claude-3-opus", "claude-3-sonnet"
            ]


# Función de conveniencia para crear cliente
def create_llm_client(
    model: str = "llama3.2",
    provider: str = "auto",
    base_url: str = "",
    api_key: str = ""
) -> UnifiedLLMClient:
    """
    Crear cliente LLM apropiado según el modelo

    Args:
        model: Nombre del modelo (ej: "llama3.2", "gpt-4o", "minimax-m2.7:cloud")
        provider: Proveedor ("ollama", "openai", "minimax", "auto")
        base_url: URL base del API (opcional)
        api_key: API key (opcional para Ollama local)

    Returns:
        Cliente LLM unificado

    Examples:
        # Ollama local
        client = create_llm_client(model="llama3.2")

        # MiniMax Cloud
        client = create_llm_client(
            model="minimax-m2.7:cloud",
            api_key="tu-api-key"
        )

        # OpenAI
        client = create_llm_client(
            model="gpt-4o",
            api_key="tu-api-key"
        )
    """
    return UnifiedLLMClient(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model
    )