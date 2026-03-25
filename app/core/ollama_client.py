"""
Cliente para Ollama Cloud API
Soporta cualquier modelo disponible en https://ollama.com/search
"""

import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any, AsyncIterator

logger = logging.getLogger(__name__)


class OllamaClient:
    """Cliente para interactuar con Ollama Cloud API"""

    def __init__(
        self,
        base_url: str = "https://api.ollama.ai",
        api_key: str = "",
        model: str = "llama3.2"
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.headers = {
            "Content-Type": "application/json"
        }
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def set_model(self, model: str) -> None:
        """Cambiar el modelo dinámicamente"""
        self.model = model
        logger.info(f"Modelo cambiado a: {model}")

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

    async def chat(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Enviar mensaje de chat a Ollama

        Args:
            messages: Lista de mensajes en formato [{"role": "user/assistant", "content": "..."}]
            tools: Lista de herramientas disponibles (function calling)
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
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "message": data.get("message", {}),
                            "model": self.model
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Error en Ollama API: {error_text}")
                        return {
                            "success": False,
                            "error": f"API Error: {response.status}",
                            "details": error_text
                        }
        except Exception as e:
            logger.error(f"Excepción en chat: {e}")
            return {
                "success": False,
                "error": str(e)
            }

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
                    timeout=aiohttp.ClientTimeout(total=120)
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
            return {
                "success": False,
                "error": str(e)
            }

    async def get_available_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        import requests
        try:
            url = f"{self.base_url}/api/tags"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Error obteniendo modelos: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """Descargar/instalar un modelo"""
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