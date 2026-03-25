"""Cliente para comunicarse con el servicio IA Assistant"""

import aiohttp
import logging
from typing import Optional, Dict, Any, List

_LOGGER = logging.getLogger(__name__)


class IAClient:
    """Cliente HTTP para comunicarse con el backend IA Assistant"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        api_key: str = ""
    ):
        self.base_url = f"http://{host}:{port}"
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtener sesión HTTP"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Cerrar sesión HTTP"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def chat(
        self,
        message: str,
        language: str = "es",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Enviar mensaje al asistente

        Args:
            message: Mensaje del usuario
            language: Código de idioma
            context: Contexto adicional (estado de dispositivos, etc.)

        Returns:
            Respuesta del asistente
        """
        url = f"{self.base_url}/api/chat"
        payload = {
            "message": message,
            "language": language,
            "context": context or {}
        }

        try:
            session = await self._get_session()
            async with session.post(
                url,
                json=payload,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    _LOGGER.error(f"Error en chat: {error}")
                    return {"success": False, "error": error}
        except Exception as e:
            _LOGGER.error(f"Excepción en chat: {e}")
            return {"success": False, "error": str(e)}

    async def get_entities(
        self,
        domain: Optional[str] = None,
        area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Obtener lista de entidades"""
        url = f"{self.base_url}/api/entities"
        params = {}
        if domain:
            params["domain"] = domain
        if area:
            params["area"] = area

        try:
            session = await self._get_session()
            async with session.get(
                url,
                params=params,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("entities", [])
                return []
        except Exception as e:
            _LOGGER.error(f"Error obteniendo entidades: {e}")
            return []

    async def execute_action(
        self,
        action: str,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Ejecutar acción en Home Assistant"""
        url = f"{self.base_url}/api/service"
        payload = {
            "action": action,
            "params": params or {}
        }

        try:
            session = await self._get_session()
            async with session.post(
                url,
                json=payload,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error = await response.text()
                    return {"success": False, "error": error}
        except Exception as e:
            _LOGGER.error(f"Error ejecutando acción: {e}")
            return {"success": False, "error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Obtener estado del servicio"""
        url = f"{self.base_url}/api/status"

        try:
            session = await self._get_session()
            async with session.get(
                url,
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {"status": "error"}
        except Exception as e:
            _LOGGER.error(f"Error obteniendo estado: {e}")
            return {"status": "error", "error": str(e)}

    async def set_model(self, model: str) -> bool:
        """Cambiar modelo de IA"""
        url = f"{self.base_url}/api/model"
        payload = {"model": model}

        try:
            session = await self._get_session()
            async with session.put(
                url,
                json=payload,
                headers=self.headers
            ) as response:
                return response.status == 200
        except Exception as e:
            _LOGGER.error(f"Error cambiando modelo: {e}")
            return False