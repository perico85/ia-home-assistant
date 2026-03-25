"""
Ejecutor de acciones del asistente
Procesa las decisiones del modelo y ejecuta acciones en Home Assistant
"""

import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Ejecutor de acciones que procesa las decisiones del modelo IA
    y las ejecuta en Home Assistant con seguridad y logging.
    """

    # Acciones que requieren confirmación del usuario
    CRITICAL_ACTIONS = [
        "delete_automation",
        "update_config",
        "restart_homeassistant",
        "delete_entity"
    ]

    # Acciones bloqueadas (nunca se ejecutan)
    BLOCKED_ACTIONS = [
        "delete_all_entities",
        "modify_user_credentials",
        "disable_security"
    ]

    def __init__(self, ha_client, security_mode: str = "hybrid"):
        """
        Inicializar ejecutor

        Args:
            ha_client: Cliente de Home Assistant
            security_mode: Modo de seguridad (safe, hybrid, unrestricted)
        """
        self.ha_client = ha_client
        self.security_mode = security_mode
        self.action_log: List[Dict] = []
        self.rollback_stack: List[Dict] = []

        # Registro de manejadores de acciones
        self.action_handlers: Dict[str, Callable] = {
            "get_entities": self._handle_get_entities,
            "get_state": self._handle_get_state,
            "call_service": self._handle_call_service,
            "turn_on": self._handle_turn_on,
            "turn_off": self._handle_turn_off,
            "toggle": self._handle_toggle,
            "set_value": self._handle_set_value,
            "create_automation": self._handle_create_automation,
            "update_automation": self._handle_update_automation,
            "delete_automation": self._handle_delete_automation,
            "execute_script": self._handle_execute_script,
            "activate_scene": self._handle_activate_scene,
            "get_automations": self._handle_get_automations,
            "get_logs": self._handle_get_logs,
            "get_areas": self._handle_get_areas,
            "restart_ha": self._handle_restart_ha,
        }

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar una acción

        Args:
            action: Diccionario con la acción a ejecutar
                {
                    "name": "nombre_accion",
                    "params": {...},
                    "confirmation_required": False
                }

        Returns:
            Resultado de la ejecución
        """
        action_name = action.get("name")
        params = action.get("params", {})

        # Verificar si la acción está bloqueada
        if action_name in self.BLOCKED_ACTIONS:
            return {
                "success": False,
                "error": f"Acción bloqueada: {action_name}",
                "blocked": True
            }

        # Verificar si requiere confirmación (modo híbrido)
        requires_confirmation = (
            action_name in self.CRITICAL_ACTIONS and
            self.security_mode == "hybrid"
        )

        if requires_confirmation and not action.get("confirmed", False):
            return {
                "success": False,
                "requires_confirmation": True,
                "action": action,
                "message": f"La acción '{action_name}' requiere confirmación"
            }

        # Registrar inicio de acción
        action_record = {
            "action": action_name,
            "params": params,
            "timestamp_start": datetime.now().isoformat(),
            "success": False
        }

        try:
            # Obtener manejador
            handler = self.action_handlers.get(action_name)

            if not handler:
                return {
                    "success": False,
                    "error": f"Acción no reconocida: {action_name}"
                }

            # Ejecutar
            result = await handler(params)

            # Actualizar registro
            action_record["success"] = result.get("success", False)
            action_record["timestamp_end"] = datetime.now().isoformat()
            action_record["result"] = result

            # Añadir al log
            self.action_log.append(action_record)

            return result

        except Exception as e:
            logger.error(f"Error ejecutando acción {action_name}: {e}")
            action_record["error"] = str(e)
            action_record["timestamp_end"] = datetime.now().isoformat()
            self.action_log.append(action_record)

            return {
                "success": False,
                "error": str(e)
            }

    async def confirm_and_execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar una acción previamente confirmada

        Args:
            action: Acción confirmada

        Returns:
            Resultado de la ejecución
        """
        action["confirmed"] = True
        return await self.execute(action)

    # ==================== HANDLERS ====================

    async def _handle_get_entities(self, params: Dict) -> Dict[str, Any]:
        """Manejador para obtener entidades"""
        domain = params.get("domain")
        area = params.get("area")
        device_class = params.get("device_class")

        entities = await self.ha_client.get_entities(
            domain=domain,
            area=area,
            device_class=device_class
        )

        return {
            "success": True,
            "entities": entities,
            "count": len(entities)
        }

    async def _handle_get_state(self, params: Dict) -> Dict[str, Any]:
        """Manejador para obtener estado de entidad"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id requerido"}

        state = await self.ha_client.get_state(entity_id)

        if state:
            return {
                "success": True,
                "entity_id": entity_id,
                "state": state.get("state"),
                "attributes": state.get("attributes", {})
            }
        else:
            return {
                "success": False,
                "error": f"Entidad no encontrada: {entity_id}"
            }

    async def _handle_call_service(self, params: Dict) -> Dict[str, Any]:
        """Manejador para llamar servicio"""
        domain = params.get("domain")
        service = params.get("service")
        entity_id = params.get("entity_id")
        service_data = params.get("data", {})

        if not domain or not service:
            return {"success": False, "error": "domain y service requeridos"}

        success = await self.ha_client.call_service(
            domain=domain,
            service=service,
            entity_id=entity_id,
            service_data=service_data
        )

        return {
            "success": success,
            "action": f"{domain}.{service}",
            "entity_id": entity_id
        }

    async def _handle_turn_on(self, params: Dict) -> Dict[str, Any]:
        """Manejador para encender entidad"""
        entity_id = params.get("entity_id")
        brightness = params.get("brightness")

        if not entity_id:
            return {"success": False, "error": "entity_id requerido"}

        success = await self.ha_client.turn_on(entity_id, brightness)

        # Guardar para rollback
        if success:
            self._save_rollback("turn_off", {"entity_id": entity_id})

        return {
            "success": success,
            "entity_id": entity_id,
            "action": "turn_on"
        }

    async def _handle_turn_off(self, params: Dict) -> Dict[str, Any]:
        """Manejador para apagar entidad"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id requerido"}

        success = await self.ha_client.turn_off(entity_id)

        if success:
            self._save_rollback("turn_on", {"entity_id": entity_id})

        return {
            "success": success,
            "entity_id": entity_id,
            "action": "turn_off"
        }

    async def _handle_toggle(self, params: Dict) -> Dict[str, Any]:
        """Manejador para alternar estado"""
        entity_id = params.get("entity_id")

        if not entity_id:
            return {"success": False, "error": "entity_id requerido"}

        success = await self.ha_client.toggle(entity_id)

        return {
            "success": success,
            "entity_id": entity_id,
            "action": "toggle"
        }

    async def _handle_set_value(self, params: Dict) -> Dict[str, Any]:
        """Manejador para establecer valor"""
        entity_id = params.get("entity_id")
        value = params.get("value")

        if not entity_id or value is None:
            return {"success": False, "error": "entity_id y value requeridos"}

        success = await self.ha_client.set_value(entity_id, value)

        return {
            "success": success,
            "entity_id": entity_id,
            "value": value,
            "action": "set_value"
        }

    async def _handle_create_automation(self, params: Dict) -> Dict[str, Any]:
        """Manejador para crear automatización"""
        config = params.get("config", {})

        if not config:
            return {"success": False, "error": "config requerido"}

        success = await self.ha_client.create_automation(config)

        return {
            "success": success,
            "automation_id": config.get("id"),
            "action": "create_automation"
        }

    async def _handle_update_automation(self, params: Dict) -> Dict[str, Any]:
        """Manejador para actualizar automatización"""
        automation_id = params.get("automation_id")
        config = params.get("config", {})

        if not automation_id or not config:
            return {"success": False, "error": "automation_id y config requeridos"}

        success = await self.ha_client.update_automation(automation_id, config)

        return {
            "success": success,
            "automation_id": automation_id,
            "action": "update_automation"
        }

    async def _handle_delete_automation(self, params: Dict) -> Dict[str, Any]:
        """Manejador para eliminar automatización"""
        automation_id = params.get("automation_id")

        if not automation_id:
            return {"success": False, "error": "automation_id requerido"}

        # Guardar configuración actual para rollback
        current_config = await self.ha_client.get_automation_config(automation_id)
        if current_config:
            self._save_rollback("create_automation", {"config": current_config})

        success = await self.ha_client.delete_automation(automation_id)

        return {
            "success": success,
            "automation_id": automation_id,
            "action": "delete_automation"
        }

    async def _handle_execute_script(self, params: Dict) -> Dict[str, Any]:
        """Manejador para ejecutar script"""
        script_id = params.get("script_id")
        variables = params.get("variables", {})

        if not script_id:
            return {"success": False, "error": "script_id requerido"}

        success = await self.ha_client.execute_script(script_id, variables)

        return {
            "success": success,
            "script_id": script_id,
            "action": "execute_script"
        }

    async def _handle_activate_scene(self, params: Dict) -> Dict[str, Any]:
        """Manejador para activar escena"""
        scene_id = params.get("scene_id")

        if not scene_id:
            return {"success": False, "error": "scene_id requerido"}

        success = await self.ha_client.activate_scene(scene_id)

        return {
            "success": success,
            "scene_id": scene_id,
            "action": "activate_scene"
        }

    async def _handle_get_automations(self, params: Dict) -> Dict[str, Any]:
        """Manejador para obtener automatizaciones"""
        automations = await self.ha_client.get_automations()

        return {
            "success": True,
            "automations": automations,
            "count": len(automations)
        }

    async def _handle_get_logs(self, params: Dict) -> Dict[str, Any]:
        """Manejador para obtener logs"""
        entity_id = params.get("entity_id")
        start_time = params.get("start_time")
        end_time = params.get("end_time")

        logs = await self.ha_client.get_logbook(
            entity_id=entity_id,
            start_time=start_time,
            end_time=end_time
        )

        return {
            "success": True,
            "logs": logs
        }

    async def _handle_get_areas(self, params: Dict) -> Dict[str, Any]:
        """Manejador para obtener áreas"""
        areas = await self.ha_client.get_areas()

        return {
            "success": True,
            "areas": areas
        }

    async def _handle_restart_ha(self, params: Dict) -> Dict[str, Any]:
        """Manejador para reiniciar Home Assistant"""
        success = await self.ha_client.restart_homeassistant()

        return {
            "success": success,
            "action": "restart_homeassistant"
        }

    # ==================== UTILIDADES ====================

    def _save_rollback(self, action: str, params: Dict) -> None:
        """Guardar acción de rollback"""
        self.rollback_stack.append({
            "action": action,
            "params": params,
            "timestamp": datetime.now().isoformat()
        })

    async def rollback_last(self) -> Dict[str, Any]:
        """Deshacer última acción"""
        if not self.rollback_stack:
            return {"success": False, "error": "No hay acciones para deshacer"}

        rollback_action = self.rollback_stack.pop()

        # Ejecutar acción de rollback
        action_name = rollback_action["action"]
        params = rollback_action["params"]

        handler = self.action_handlers.get(action_name)
        if handler:
            return await handler(params)

        return {"success": False, "error": f"No hay handler para rollback: {action_name}"}

    def get_action_log(self, limit: int = 100) -> List[Dict]:
        """Obtener log de acciones"""
        return self.action_log[-limit:]

    def clear_action_log(self) -> None:
        """Limpiar log de acciones"""
        self.action_log.clear()

    def get_available_actions(self) -> List[Dict]:
        """Obtener lista de acciones disponibles"""
        return [
            {
                "name": name,
                "description": handler.__doc__ or "Sin descripción"
            }
            for name, handler in self.action_handlers.items()
        ]