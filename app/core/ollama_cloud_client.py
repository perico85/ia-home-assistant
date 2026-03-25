"""
Cliente para Ollama Cloud
Soporta modelos locales y modelos cloud de Ollama

Ollama Cloud permite usar modelos potentes en la nube sin instalarlos localmente.
Ver: https://docs.ollama.com/cloud
"""

import os
import logging
from typing import Optional, List, Dict, Any, AsyncIterator

try:
    import ollama
    HAS_OLLAMA_SDK = True
except ImportError:
    HAS_OLLAMA_SDK = False

import aiohttp
import json

logger = logging.getLogger(__name__)


class OllamaCloudClient:
    """
    Cliente para Ollama y Ollama Cloud usando el SDK oficial

    Soporta:
    - Ollama local (http://localhost:11434)
    - Ollama Cloud (https://ollama.com)
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

        # Inicializar cliente Ollama SDK
        self._client = None
        if HAS_OLLAMA_SDK:
            self._init_client()

        logger.info(f"OllamaClient inicializado: modelo={model}, cloud={self.is_cloud}, endpoint={self.base_url}")

    def _init_client(self):
        """Inicializar el cliente del SDK de Ollama"""
        headers = {}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        self._client = ollama.Client(
            host=self.base_url,
            headers=headers if headers else None
        )

    def _is_cloud_model(self, model: str) -> bool:
        """Detectar si un modelo es de cloud basándose en el nombre"""
        cloud_models = [
            "minimax", "gpt-oss", "command-r",
            "llama3.2", "llama3.1", "llama3",
            "gemini", "gpt-4", "gpt-3.5",
            "mixtral-8x22b", "deepseek"
        ]
        model_lower = model.lower()
        return ":cloud" in model_lower or any(m in model_lower for m in cloud_models)

    def set_model(self, model: str) -> None:
        """Cambiar modelo dinámicamente"""
        self.model = model
        was_cloud = self.is_cloud
        self.is_cloud = ":cloud" in model or self._is_cloud_model(model)

        # Cambiar endpoint si cambió el tipo
        if self.is_cloud and not was_cloud:
            self.base_url = self.CLOUD_ENDPOINT
            if self._client:
                self._init_client()
            logger.info(f"Cambiado a Ollama Cloud: {model}")
        elif not self.is_cloud and was_cloud:
            self.base_url = self.LOCAL_ENDPOINT
            if self._client:
                self._init_client()
            logger.info(f"Cambiado a Ollama local: {model}")

    def test_connection(self) -> bool:
        """Verificar conexión con Ollama"""
        try:
            if self._client:
                # Usar SDK
                self._client.list()
                return True
            else:
                # Fallback a HTTP
                import requests
                url = f"{self.base_url}/api/tags"
                headers = {}
                if self.api_key:
                    headers['Authorization'] = f'Bearer {self.api_key}'
                response = requests.get(url, headers=headers, timeout=10)
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Error conectando a Ollama: {e}")
            return False

    async def get_available_models(self) -> List[str]:
        """Obtener lista de modelos disponibles"""
        try:
            if self._client:
                models = self._client.list()
                return [m['model'] for m in models.get('models', [])]
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
        try:
            if self._client and not stream:
                # Usar SDK de Ollama
                kwargs = {
                    'model': self.model,
                    'messages': messages,
                }
                if tools:
                    kwargs['tools'] = tools

                response = self._client.chat(**kwargs)

                # Extraer contenido
                message = response.get('message', {})
                return {
                    'success': True,
                    'message': message,
                    'model': response.get('model', self.model),
                    'done': response.get('done', True)
                }
            else:
                # Fallback a HTTP o streaming
                return await self._chat_http(messages, tools, stream)

        except Exception as e:
            logger.error(f"Error en chat: {e}")
            return {'success': False, 'error': str(e)}

    async def _chat_http(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Chat usando HTTP directo"""
        url = f"{self.base_url}/api/chat"

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        payload = {
            'model': self.model,
            'messages': messages,
            'stream': stream
        }
        if tools:
            payload['tools'] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'message': data.get('message', {}),
                            'model': self.model,
                            'done': data.get('done', True)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Error en Ollama API: {error_text}")
                        return {
                            'success': False,
                            'error': f"API Error: {response.status}",
                            'details': error_text
                        }
        except Exception as e:
            logger.error(f"Excepción en chat HTTP: {e}")
            return {'success': False, 'error': str(e)}

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None
    ) -> AsyncIterator[str]:
        """
        Chat con streaming para respuestas en tiempo real
        """
        url = f"{self.base_url}/api/chat"

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        payload = {
            'model': self.model,
            'messages': messages,
            'stream': True
        }
        if tools:
            payload['tools'] = tools

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
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
        """Generar respuesta simple"""
        url = f"{self.base_url}/api/generate"

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        payload = {
            'model': self.model,
            'prompt': prompt,
            'stream': False
        }
        if system:
            payload['system'] = system
        if context:
            payload['context'] = context

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'response': data.get('response', ''),
                            'context': data.get('context', [])
                        }
                    else:
                        return {
                            'success': False,
                            'error': f"API Error: {response.status}"
                        }
        except Exception as e:
            return {'success': False, 'error': str(e)}


def create_ollama_client(
    model: str = "llama3.2",
    api_key: Optional[str] = None,
    use_cloud: bool = False,
    base_url: Optional[str] = None
) -> OllamaCloudClient:
    """
    Crear cliente de Ollama configurado correctamente

    Args:
        model: Nombre del modelo
        api_key: API key para Ollama Cloud
        use_cloud: Si True, usa Ollama Cloud
        base_url: URL base personalizada

    Returns:
        Cliente configurado
    """
    return OllamaCloudClient(
        model=model,
        api_key=api_key,
        use_cloud=use_cloud,
        base_url=base_url
    )