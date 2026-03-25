"""
Sistema de seguridad para el asistente IA
Validación de acciones, rate limiting y control de acceso
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from functools import wraps
import json

logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Gestor de seguridad para el asistente IA
    Controla permisos, validaciones y restricciones
    """

    # Acciones que requieren confirmación del usuario
    CRITICAL_ACTIONS = [
        "delete_automation",
        "delete_script",
        "delete_scene",
        "update_config",
        "restart_homeassistant",
        "reload_core_config"
    ]

    # Acciones completamente bloqueadas
    BLOCKED_ACTIONS = [
        "delete_all_entities",
        "modify_user_credentials",
        "disable_security",
        "reset_password",
        "delete_all_automations"
    ]

    # Límites de rate por acción
    RATE_LIMITS = {
        "turn_on": 60,      # 60 por minuto
        "turn_off": 60,
        "toggle": 60,
        "call_service": 60,
        "create_automation": 10,
        "delete_automation": 5,
        "get_state": 120,
        "get_entities": 60
    }

    def __init__(self, security_mode: str = "hybrid"):
        """
        Inicializar gestor de seguridad

        Args:
            security_mode: Modo de seguridad (safe, hybrid, unrestricted)
        """
        self.security_mode = security_mode
        self.action_history: Dict[str, List[datetime]] = defaultdict(list)
        self.pending_confirmations: Dict[str, Dict] = {}
        self.audit_log: List[Dict] = []

    def validate_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validar si una acción puede ejecutarse

        Args:
            action: Acción a validar

        Returns:
            Resultado de la validación
        """
        action_name = action.get("name", "")
        params = action.get("params", {})

        result = {
            "valid": True,
            "requires_confirmation": False,
            "blocked": False,
            "message": ""
        }

        # Verificar si está bloqueada
        if action_name in self.BLOCKED_ACTIONS:
            result["valid"] = False
            result["blocked"] = True
            result["message"] = f"Acción bloqueada por seguridad: {action_name}"
            self._log_audit(action, "blocked", result["message"])
            return result

        # Verificar rate limit
        if not self._check_rate_limit(action_name):
            result["valid"] = False
            result["message"] = f"Rate limit excedido para {action_name}"
            self._log_audit(action, "rate_limited", result["message"])
            return result

        # Verificar si requiere confirmación (modo híbrido)
        if self.security_mode == "hybrid":
            if action_name in self.CRITICAL_ACTIONS:
                result["requires_confirmation"] = True
                result["message"] = f"La acción {action_name} requiere confirmación"
                self._log_audit(action, "pending_confirmation", result["message"])
                return result

        # Validar parámetros
        validation_result = self._validate_params(action_name, params)
        if not validation_result["valid"]:
            result["valid"] = False
            result["message"] = validation_result["message"]
            self._log_audit(action, "invalid_params", result["message"])
            return result

        # Acción válida
        self._log_audit(action, "approved", "Acción aprobada")
        return result

    def _check_rate_limit(self, action_name: str) -> bool:
        """
        Verificar rate limit

        Args:
            action_name: Nombre de la acción

        Returns:
            True si está dentro del límite
        """
        limit = self.RATE_LIMITS.get(action_name)
        if not limit:
            return True

        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Limpiar historial antiguo
        self.action_history[action_name] = [
            t for t in self.action_history[action_name]
            if t > minute_ago
        ]

        # Verificar límite
        if len(self.action_history[action_name]) >= limit:
            return False

        # Registrar acción
        self.action_history[action_name].append(now)
        return True

    def _validate_params(
        self,
        action_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validar parámetros de una acción

        Args:
            action_name: Nombre de la acción
            params: Parámetros a validar

        Returns:
            Resultado de la validación
        """
        result = {"valid": True, "message": ""}

        # Validaciones específicas por acción
        if action_name in ["turn_on", "turn_off", "toggle"]:
            if "entity_id" not in params:
                return {"valid": False, "message": "entity_id es requerido"}

            entity_id = params["entity_id"]
            if not self._is_valid_entity_id(entity_id):
                return {"valid": False, "message": f"entity_id inválido: {entity_id}"}

        elif action_name == "set_value":
            if "entity_id" not in params or "value" not in params:
                return {"valid": False, "message": "entity_id y value son requeridos"}

        elif action_name == "call_service":
            if "domain" not in params or "service" not in params:
                return {"valid": False, "message": "domain y service son requeridos"}

        elif action_name == "create_automation":
            if "config" not in params:
                return {"valid": False, "message": "config es requerido"}
            if not self._validate_automation_config(params["config"]):
                return {"valid": False, "message": "Configuración de automatización inválida"}

        return result

    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Verificar si un entity_id tiene formato válido"""
        import re
        pattern = r'^[a-z_]+\.[a-z_0-9]+$'
        return bool(re.match(pattern, entity_id))

    def _validate_automation_config(self, config: Dict) -> bool:
        """Validar configuración de automatización"""
        required_keys = ["id", "trigger", "action"]
        return all(k in config for k in required_keys)

    def _log_audit(
        self,
        action: Dict,
        status: str,
        message: str
    ):
        """Registrar en log de auditoría"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action.get("name"),
            "params": action.get("params"),
            "status": status,
            "message": message
        }
        self.audit_log.append(entry)

        # Mantener solo los últimos 1000 registros
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]

    def request_confirmation(
        self,
        action: Dict[str, Any],
        timeout: int = 300
    ) -> str:
        """
        Solicitar confirmación para una acción

        Args:
            action: Acción pendiente
            timeout: Tiempo de espera en segundos

        Returns:
            ID de confirmación
        """
        import uuid
        confirmation_id = str(uuid.uuid4())

        self.pending_confirmations[confirmation_id] = {
            "action": action,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(seconds=timeout)
        }

        return confirmation_id

    def confirm_action(self, confirmation_id: str) -> Dict[str, Any]:
        """
        Confirmar una acción pendiente

        Args:
            confirmation_id: ID de confirmación

        Returns:
            Acción confirmada o error
        """
        if confirmation_id not in self.pending_confirmations:
            return {"valid": False, "message": "ID de confirmación inválido"}

        pending = self.pending_confirmations[confirmation_id]

        # Verificar expiración
        if datetime.now() > pending["expires_at"]:
            del self.pending_confirmations[confirmation_id]
            return {"valid": False, "message": "Confirmación expirada"}

        action = pending["action"]
        del self.pending_confirmations[confirmation_id]

        self._log_audit(action, "confirmed", "Acción confirmada por usuario")
        return {"valid": True, "action": action}

    def cancel_confirmation(self, confirmation_id: str) -> bool:
        """Cancelar una confirmación pendiente"""
        if confirmation_id in self.pending_confirmations:
            del self.pending_confirmations[confirmation_id]
            return True
        return False

    def get_pending_confirmations(self) -> List[Dict]:
        """Obtener confirmaciones pendientes"""
        return [
            {"id": k, "action": v["action"]}
            for k, v in self.pending_confirmations.items()
        ]

    def get_audit_log(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Obtener log de auditoría filtrado

        Args:
            start_time: Tiempo inicial
            end_time: Tiempo final
            status: Filtrar por estado
            limit: Límite de resultados

        Returns:
            Lista de registros
        """
        logs = self.audit_log

        if status:
            logs = [l for l in logs if l.get("status") == status]

        if start_time:
            logs = [l for l in logs if l.get("timestamp", "") >= start_time.isoformat()]

        if end_time:
            logs = [l for l in logs if l.get("timestamp", "") <= end_time.isoformat()]

        return logs[-limit:]

    def export_audit_log(self) -> str:
        """Exportar log de auditoría como JSON"""
        return json.dumps(self.audit_log, indent=2, ensure_ascii=False)


def require_confirmation(func: Callable) -> Callable:
    """
    Decorador para acciones que requieren confirmación

    Args:
        func: Función a decorar

    Returns:
        Función decorada
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        action = kwargs.get('action', {})

        # Si ya está confirmada, ejecutar
        if action.get('confirmed', False):
            return await func(self, *args, **kwargs)

        # Si no, solicitar confirmación
        # El SecurityManager manejará la lógica
        security_manager = getattr(self, 'security_manager', None)
        if security_manager:
            confirmation_id = security_manager.request_confirmation(action)
            return {
                "requires_confirmation": True,
                "confirmation_id": confirmation_id,
                "message": "Esta acción requiere confirmación"
            }

        return await func(self, *args, **kwargs)

    return wrapper


def rate_limit(limit: int, window: int = 60) -> Callable:
    """
    Decorador para rate limiting

    Args:
        limit: Número máximo de llamadas
        window: Ventana de tiempo en segundos

    Returns:
        Decorador
    """
    calls = defaultdict(list)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Obtener identificador único (por ejemplo, entity_id o session_id)
            identifier = kwargs.get('entity_id', kwargs.get('session_id', 'default'))

            now = datetime.now()
            window_start = now - timedelta(seconds=window)

            # Limpiar llamadas antiguas
            calls[identifier] = [
                t for t in calls[identifier] if t > window_start
            ]

            # Verificar límite
            if len(calls[identifier]) >= limit:
                return {
                    "success": False,
                    "error": "Rate limit excedido"
                }

            # Registrar llamada
            calls[identifier].append(now)

            return await func(*args, **kwargs)

        return wrapper

    return decorator