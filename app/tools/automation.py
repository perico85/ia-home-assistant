"""
Herramientas de automatización para el asistente IA
"""

from typing import Dict, Any, List, Optional
import yaml


def get_automation_tools() -> List[Dict[str, Any]]:
    """Obtener definiciones de herramientas de automatización"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_automations",
                "description": "Obtener lista de todas las automatizaciones",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_automation_config",
                "description": "Obtener configuración detallada de una automatización",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "automation_id": {
                            "type": "string",
                            "description": "ID de la automatización"
                        }
                    },
                    "required": ["automation_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_automation",
                "description": "Crear una nueva automatización",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre de la automatización"
                        },
                        "description": {
                            "type": "string",
                            "description": "Descripción de la automatización"
                        },
                        "triggers": {
                            "type": "array",
                            "description": "Lista de triggers",
                            "items": {
                                "type": "object"
                            }
                        },
                        "conditions": {
                            "type": "array",
                            "description": "Lista de condiciones",
                            "items": {
                                "type": "object"
                            }
                        },
                        "actions": {
                            "type": "array",
                            "description": "Lista de acciones",
                            "items": {
                                "type": "object"
                            }
                        }
                    },
                    "required": ["name", "triggers", "actions"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_automation",
                "description": "Actualizar una automatización existente",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "automation_id": {
                            "type": "string",
                            "description": "ID de la automatización a actualizar"
                        },
                        "config": {
                            "type": "object",
                            "description": "Nueva configuración"
                        }
                    },
                    "required": ["automation_id", "config"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "delete_automation",
                "description": "Eliminar una automatización",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "automation_id": {
                            "type": "string",
                            "description": "ID de la automatización a eliminar"
                        }
                    },
                    "required": ["automation_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle_automation",
                "description": "Activar o desactivar una automatización",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "automation_id": {
                            "type": "string",
                            "description": "ID de la automatización"
                        },
                        "enabled": {
                            "type": "boolean",
                            "description": "True para activar, False para desactivar"
                        }
                    },
                    "required": ["automation_id", "enabled"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_automation",
                "description": "Ejecutar manualmente una automatización",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "automation_id": {
                            "type": "string",
                            "description": "ID de la automatización"
                        }
                    },
                    "required": ["automation_id"]
                }
            }
        }
    ]


def build_automation_config(
    name: str,
    triggers: List[Dict],
    actions: List[Dict],
    conditions: Optional[List[Dict]] = None,
    description: str = "",
    mode: str = "single",
    max_exceeded: int = 10
) -> Dict[str, Any]:
    """
    Construir configuración de automatización

    Args:
        name: Nombre de la automatización
        triggers: Lista de triggers
        actions: Lista de acciones
        conditions: Lista de condiciones (opcional)
        description: Descripción
        mode: Modo (single, restart, queue, parallel)
        max_exceeded: Máximo de ejecuciones excedidas

    Returns:
        Configuración de automatización
    """
    automation_id = name.lower().replace(" ", "_").replace("-", "_")

    config = {
        "id": automation_id,
        "alias": name,
        "description": description,
        "trigger": triggers,
        "action": actions,
        "mode": mode,
        "max_exceeded": str(max_exceeded)
    }

    if conditions:
        config["condition"] = conditions

    return config


def create_trigger(
    trigger_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Crear configuración de trigger

    Args:
        trigger_type: Tipo de trigger (state, time, device, etc.)
        **kwargs: Parámetros específicos del trigger

    Returns:
        Configuración del trigger
    """
    trigger = {"platform": trigger_type}

    if trigger_type == "state":
        trigger["entity_id"] = kwargs.get("entity_id")
        trigger["from"] = kwargs.get("from_state")
        trigger["to"] = kwargs.get("to_state")
        if kwargs.get("attribute"):
            trigger["attribute"] = kwargs.get("attribute")

    elif trigger_type == "time":
        trigger["at"] = kwargs.get("at")

    elif trigger_type == "device":
        trigger["device_id"] = kwargs.get("device_id")
        trigger["domain"] = kwargs.get("domain", "mobile_app")
        trigger["type"] = kwargs.get("type")

    elif trigger_type == "sun":
        trigger["event"] = kwargs.get("event", "sunrise")
        trigger["offset"] = kwargs.get("offset")

    elif trigger_type == "zone":
        trigger["entity_id"] = kwargs.get("entity_id")
        trigger["zone"] = kwargs.get("zone")
        trigger["event"] = kwargs.get("event", "enter")

    elif trigger_type == "webhook":
        trigger["webhook_id"] = kwargs.get("webhook_id")

    elif trigger_type == "numeric_state":
        trigger["entity_id"] = kwargs.get("entity_id")
        trigger["above"] = kwargs.get("above")
        trigger["below"] = kwargs.get("below")

    # Añadir parámetros adicionales
    for key, value in kwargs.items():
        if key not in trigger:
            trigger[key] = value

    return trigger


def create_action(
    action_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Crear configuración de acción

    Args:
        action_type: Tipo de acción (service, delay, condition, etc.)
        **kwargs: Parámetros específicos de la acción

    Returns:
        Configuración de la acción
    """
    if action_type == "service":
        action = {
            "service": kwargs.get("service"),
            "target": kwargs.get("target", kwargs.get("entity_id")),
        }
        if kwargs.get("data"):
            action["data"] = kwargs.get("data")

    elif action_type == "delay":
        action = {"delay": kwargs.get("seconds", 0)}

    elif action_type == "condition":
        action = {"condition": kwargs.get("condition_type"), **kwargs}

    elif action_type == "scene":
        action = {"service": "scene.turn_on", "target": kwargs.get("scene_id")}

    elif action_type == "wait":
        action = {
            "wait_template": kwargs.get("template"),
            "timeout": kwargs.get("timeout", 300)
        }

    else:
        action = {action_type: kwargs}

    return action


def format_automation_summary(automation: Dict[str, Any]) -> str:
    """
    Formatear resumen de automatización

    Args:
        automation: Datos de la automatización

    Returns:
        Texto formateado
    """
    attrs = automation.get("attributes", {})
    name = attrs.get("friendly_name", automation.get("entity_id", "Sin nombre"))
    state = automation.get("state", "unknown")

    # Estado en español
    state_text = "activa" if state == "on" else "inactiva"

    return f"- {name}: {state_text}"


def generate_automation_yaml(config: Dict[str, Any]) -> str:
    """
    Generar YAML de automatización

    Args:
        config: Configuración de la automatización

    Returns:
        YAML formateado
    """
    return yaml.dump([config], allow_unicode=True, default_flow_style=False, sort_keys=False)