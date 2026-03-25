"""
Cliente para Home Assistant API
Proporciona acceso completo a la API de Home Assistant
"""

import aiohttp
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Cliente para interactuar con Home Assistant via REST API"""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip('/')
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> bool:
        """Verificar conexión con Home Assistant"""
        import requests
        try:
            url = f"{self.url}/api/"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error conectando a Home Assistant: {e}")
            return False

    # ==================== ENTIDADES ====================

    async def get_states(self) -> List[Dict[str, Any]]:
        """Obtener estado de todas las entidades"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/states",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []

    async def get_state(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Obtener estado de una entidad específica"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/states/{entity_id}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def get_entities(
        self,
        domain: Optional[str] = None,
        area: Optional[str] = None,
        device_class: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener entidades filtradas

        Args:
            domain: Dominio (light, switch, sensor, etc.)
            area: Área/filtro por habitación
            device_class: Clase de dispositivo

        Returns:
            Lista de entidades filtradas
        """
        states = await self.get_states()

        result = []
        for state in states:
            entity_id = state.get("entity_id", "")

            # Filtrar por dominio
            if domain and not entity_id.startswith(f"{domain}."):
                continue

            # Filtrar por área
            if area:
                attrs = state.get("attributes", {})
                if attrs.get("area_id") != area:
                    continue

            # Filtrar por device_class
            if device_class:
                attrs = state.get("attributes", {})
                if attrs.get("device_class") != device_class:
                    continue

            result.append(state)

        return result

    # ==================== SERVICIOS ====================

    async def call_service(
        self,
        domain: str,
        service: str,
        entity_id: Optional[str] = None,
        service_data: Optional[Dict] = None
    ) -> bool:
        """
        Llamar a un servicio de Home Assistant

        Args:
            domain: Dominio (light, switch, climate, etc.)
            service: Servicio (turn_on, turn_off, toggle, etc.)
            entity_id: ID de la entidad
            service_data: Datos adicionales del servicio

        Returns:
            True si el servicio fue llamado exitosamente
        """
        url = f"{self.url}/api/services/{domain}/{service}"

        data = service_data or {}
        if entity_id:
            data["entity_id"] = entity_id

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=self.headers,
                json=data
            ) as response:
                return response.status == 200

    async def turn_on(self, entity_id: str, brightness: Optional[int] = None) -> bool:
        """Encender una entidad"""
        domain = entity_id.split('.')[0]
        data = {}
        if brightness:
            data["brightness"] = brightness
        return await self.call_service(domain, "turn_on", entity_id, data)

    async def turn_off(self, entity_id: str) -> bool:
        """Apagar una entidad"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "turn_off", entity_id)

    async def toggle(self, entity_id: str) -> bool:
        """Alternar estado de una entidad"""
        domain = entity_id.split('.')[0]
        return await self.call_service(domain, "toggle", entity_id)

    async def set_value(self, entity_id: str, value: Any) -> bool:
        """Establecer valor de una entidad (dimmer, thermostat, etc.)"""
        domain = entity_id.split('.')[0]

        # Mapear según dominio
        if domain == "light":
            return await self.call_service(domain, "turn_on", entity_id, {"brightness": value})
        elif domain == "climate":
            return await self.call_service(domain, "set_temperature", entity_id, {"temperature": value})
        elif domain == "input_number":
            return await self.call_service(domain, "set_value", entity_id, {"value": value})
        elif domain == "input_select":
            return await self.call_service(domain, "select_option", entity_id, {"option": value})
        else:
            return await self.call_service(domain, "set_value", entity_id, {"value": value})

    # ==================== AUTOMATIZACIONES ====================

    async def get_automations(self) -> List[Dict[str, Any]]:
        """Obtener todas las automatizaciones"""
        return await self.get_entities(domain="automation")

    async def get_automation_config(self, automation_id: str) -> Optional[Dict]:
        """Obtener configuración de una automatización"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/config/automation/config/{automation_id}",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return None

    async def create_automation(self, config: Dict) -> bool:
        """Crear una nueva automatización"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.url}/api/config/automation/config/{config.get('id')}",
                headers=self.headers,
                json=config
            ) as response:
                return response.status == 200

    async def update_automation(self, automation_id: str, config: Dict) -> bool:
        """Actualizar una automatización existente"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.url}/api/config/automation/config/{automation_id}",
                headers=self.headers,
                json=config
            ) as response:
                return response.status == 200

    async def delete_automation(self, automation_id: str) -> bool:
        """Eliminar una automatización"""
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.url}/api/config/automation/config/{automation_id}",
                headers=self.headers
            ) as response:
                return response.status == 200

    # ==================== SCRIPTS ====================

    async def get_scripts(self) -> List[Dict[str, Any]]:
        """Obtener todos los scripts"""
        return await self.get_entities(domain="script")

    async def execute_script(self, script_id: str, variables: Optional[Dict] = None) -> bool:
        """Ejecutar un script"""
        return await self.call_service("script", script_id, service_data=variables)

    # ==================== ESCENAS ====================

    async def get_scenes(self) -> List[Dict[str, Any]]:
        """Obtener todas las escenas"""
        return await self.get_entities(domain="scene")

    async def activate_scene(self, scene_id: str) -> bool:
        """Activar una escena"""
        return await self.call_service("scene", "turn_on", scene_id)

    # ==================== ÁREAS ====================

    async def get_areas(self) -> List[Dict[str, Any]]:
        """Obtener todas las áreas"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/states",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    states = await response.json()
                    areas = {}
                    for state in states:
                        attrs = state.get("attributes", {})
                        area_id = attrs.get("area_id")
                        if area_id and area_id not in areas:
                            areas[area_id] = {
                                "area_id": area_id,
                                "name": attrs.get("friendly_name", area_id)
                            }
                    return list(areas.values())
                return []

    # ==================== LOGS Y DIAGNÓSTICO ====================

    async def get_logbook(
        self,
        entity_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Obtener entradas del logbook"""
        params = {}
        if entity_id:
            params["entity_id"] = entity_id
        if start_time:
            params["start_time"] = start_time.isoformat()
        if end_time:
            params["end_time"] = end_time.isoformat()

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/logbook",
                headers=self.headers,
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []

    async def get_error_log(self) -> str:
        """Obtener log de errores"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/error_log",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.text()
                return ""

    # ==================== CONFIGURACIÓN ====================

    async def get_config(self) -> Dict[str, Any]:
        """Obtener configuración de Home Assistant"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.url}/api/config",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {}

    async def check_config(self) -> Dict[str, Any]:
        """Verificar configuración"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.url}/api/config/core/check_config",
                headers=self.headers
            ) as response:
                if response.status == 200:
                    return await response.json()
                return {"valid": False, "errors": "Check failed"}

    async def restart_homeassistant(self) -> bool:
        """Reiniciar Home Assistant"""
        return await self.call_service("homeassistant", "restart")

    async def reload_core_config(self) -> bool:
        """Recargar configuración core"""
        return await self.call_service("homeassistant", "reload_core_config")

    # ==================== WEBSOCKET ====================

    async def subscribe_events(
        self,
        event_types: Optional[List[str]] = None
    ) -> None:
        """Suscribirse a eventos via WebSocket"""
        # Implementar conexión WebSocket para eventos en tiempo real
        pass