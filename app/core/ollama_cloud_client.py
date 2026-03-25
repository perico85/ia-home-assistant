"""
Cliente para Ollama Cloud
Soporta modelos locales y modelos cloud de Ollama

Ollama Cloud permite usar modelos potentes en la nube sin instalarlos localmente.
Ver: https://docs.ollama.com/cloud
"""

import aiohttp
import json
import logging
import os
from typing import Optional, List, Dict, Any, AsyncIterator

logger = logging.getLogger(__name__)


class OllamaCloudClient:
    """
    Cliente para Ollama y Ollama Cloud

    Soporta:
    - Ollama local (http://localhost:11434)
    - Ollama Cloud (https://ollama.com/api)

    Modelos cloud populares:
    - minimax-m2.7:cloud
    - gpt-oss:120b-cloud
    - llama3.2:cloud
    - Y más en: https://ollama.com/search?c=cloud
    """

    # Endpoints
    LOCAL_ENDPOINT = "http://localhost:11434"
    CLOUD_ENDPOINT = "https://ollama.com"

    def __init__(
        self,
        model: str = "llama3.2",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        use_cloud: bool = False
    ):
        """
        Inicializar cliente Ollama

        Args:
            model: Nombre del modelo (ej: "llama3.2", "minimax-m2.7:cloud")
            api_key: API key para Ollama Cloud (obtener en ollama.com/settings/keys)
            base_url: URL base personalizada (opcional)
            use_cloud: Si True, usa Ollama Cloud por defecto
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OLLAMA_API_KEY")

        # Detectar si es modelo cloud
        self.is_cloud = use_cloud or ":cloud" in model or self._is_cloud_model(model)

        # Configurar endpoint
        if base_url:
            self.base_url = base_url.rstrip('/')
        elif self.is_cloud:
            self.base_url = self.CLOUD_ENDPOINT
        else:
            self.base_url = self.LOCAL_ENDPOINT

        # Configurar headers
        self.headers = {"Content-Type": "application/json"}
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"

        logger.info(f"OllamaClient inicializado: modelo={model}, cloud={self.is_cloud}, endpoint={self.base_url}")

    def _is_cloud_model(self, model: str) -> bool:
        """Detectar si un modelo es de cloud basándose en el nombre"""
        cloud_models = [
            "minimax", "gpt-oss", "command-r", "claude",
            "gemini", "gpt-4", "gpt-3.5", "mixtral-8x22b"
        ]
        model_lower = model.lower()
        # Si contiene ":cloud" o es un modelo conocido de cloud
        return ":cloud" in model_lower or any(m in model_lower for m in cloud_models)

    def set_model(self, model: str) -> None:
        """
        Cambiar modelo dinámicamente

        El modelo puede ser:
        - Local: "llama3.2", "mistral", "codellama"
        - Cloud: "minimax-m2.7:cloud", "gpt-oss:120b-cloud"
        """
        self.model = model

        # Re-detectar si es cloud
        was_cloud = self.is_cloud
        self.is_cloud = ":cloud" in model or self._is_cloud_model(model)

        # Cambiar endpoint si cambió el tipo
        if self.is_cloud and not was_cloud:
            self.base_url = self.CLOUD_ENDPOINT
            logger.info(f"Cambiado a Ollama Cloud: {model}")
        elif not self.is_cloud and was_cloud:
            self.base_url = self.LOCAL_ENDPOINT
            logger.info(f"Cambiado a Ollama local: {model}")

    def test_connection(self) -> bool:
        """Verificar conexión con Ollama"""
        import requests
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error conectando a Ollama: {e}")
            return False

    async def get_available_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        import requests
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error obteniendo modelos: {e}")
            return []

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de chat a Ollama

        Args:
            messages: Lista de mensajes [{"role": "user/assistant", "content": "..."}]
            tools: Herramientas disponibles (function calling)
            stream: Si usar streaming

        Returns:
            Respuesta del modelo
        """
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream
        }

        if tools:
            payload["tools"] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 min timeout para cloud
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "message": data.get("message", {}),
                            "model": self.model,
                            "done": data.get("done", True)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Error en Ollama API: {error_text}")
                        return {
                            "success": False,
                            "error": f"API Error: {response.status}",
                            "details": error_text
                        }
        except aiohttp.ClientError as e:
            logger.error(f"Error de conexión: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Excepción en chat: {e}")
            return {"success": False, "error": str(e)}

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """
        Chat con streaming para respuestas en tiempo real

        Args:
            messages: Lista de mensajes
            tools: Herramientas disponibles

        Yields:
            Chunks de la respuesta
        """
        url = f"{self.base_url}/api/chat"

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True
        }

        if tools:
            payload["tools"] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
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
                                    elif 'error' in data:
                                        yield f"[Error: {data['error']}]"
                                except json.JSONDecodeError:
                                    continue
                    else:
                        error_text = await response.text()
                        yield f"[Error: API returned {response.status}]"
        except Exception as e:
            logger.error(f"Error en streaming: {e}")
            yield f"[Error: {e}]"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Generar respuesta simple (endpoint /api/generate)

        Args:
            prompt: Prompt del usuario
            system: Prompt del sistema
            context: Contexto previo

        Returns:
            Respuesta generada
        """
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }

        if system:
            payload["system"] = system
        if context:
            payload["context"] = context

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "response": data.get("response", ""),
                            "context": data.get("context", [])
                        }
                    else:
                        return {
                            "success": False,
                            "error": f"API Error: {response.status}"
                        }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def pull_model(self, model_name: str) -> bool:
        """
        Descargar/instalar un modelo

        Para modelos cloud, esto registra el acceso.
        """
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=600)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error descargando modelo: {e}")
            return False


# Función de conveniencia
def create_ollama_client(
    model: str = "llama3.2",
    api_key: Optional[str] = None,
    use_cloud: bool = False
) -> OllamaCloudClient:
    """
    Crear cliente de Ollama configurado correctamente

    Args:
        model: Nombre del modelo
        api_key: API key para Ollama Cloud (opcional para local)
        use_cloud: Si True, usa Ollama Cloud

    Returns:
        Cliente configurado

    Examples:
        # Ollama local
        client = create_ollama_client(model="llama3.2")

        # Ollama Cloud con modelo específico
        client = create_ollama_client(
            model="minimax-m2.7:cloud",
            api_key="tu-api-key"
        )

        # Forzar cloud
        client = create_ollama_client(
            model="llama3.2",
            api_key="tu-api-key",
            use_cloud=True
        )
    """
    return OllamaCloudClient(model=model, api_key=api_key, use_cloud=use_cloud)


# Lista de modelos cloud populares
CLOUD_MODELS = {
    "minimax": [
        "minimax-m2.7:cloud",
        "minimax-m1:cloud"
    ],
    "openai_compatible": [
        "gpt-oss:120b-cloud",
        "gpt-oss:70b-cloud"
    ],
    "meta": [
        "llama3.2:cloud",
        "llama3.1:70b-cloud",
        "llama3.1:405b-cloud"
    ],
    "mistral": [
        "mixtral-8x22b-cloud"
    ],
    "cohere": [
        "command-r:cloud"
    ]
}


def get_cloud_models() -> Dict[str, List[str]]:
    """Obtener lista de modelos cloud disponibles"""
    return CLOUD_MODELS.copy()