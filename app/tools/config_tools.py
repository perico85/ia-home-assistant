"""
Herramientas de configuración para el asistente IA
"""

from typing import Dict, Any, List, Optional
import yaml
import json


def get_config_tools() -> List[Dict[str, Any]]:
    """Obtener definiciones de herramientas de configuración"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_config",
                "description": "Obtener configuración general de Home Assistant",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "check_config",
                "description": "Verificar si la configuración es válida",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "reload_core_config",
                "description": "Recargar configuración core de Home Assistant",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "restart_homeassistant",
                "description": "Reiniciar Home Assistant (requiere confirmación)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmed": {
                            "type": "boolean",
                            "description": "Confirmación del usuario"
                        }
                    },
                    "required": ["confirmed"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_logbook",
                "description": "Obtener entradas del logbook",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad (opcional)"
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Horas hacia atrás (default: 24)",
                            "default": 24
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_error_log",
                "description": "Obtener log de errores",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]


def format_config_summary(config: Dict[str, Any]) -> str:
    """
    Formatear resumen de configuración

    Args:
        config: Datos de configuración

    Returns:
        Texto formateado
    """
    lines = []

    if "location_name" in config:
        lines.append(f"Ubicación: {config['location_name']}")

    if "version" in config:
        lines.append(f"Versión: {config['version']}")

    if "latitude" in config and "longitude" in config:
        lines.append(f"Coordenadas: {config['latitude']}, {config['longitude']}")

    if "time_zone" in config:
        lines.append(f"Zona horaria: {config['time_zone']}")

    if "unit_system" in config:
        units = config["unit_system"]
        lines.append(f"Unidades: {units}")

    return "\n".join(lines) if lines else "Configuración no disponible"


def format_error_log(log: str, max_lines: int = 50) -> str:
    """
    Formatear log de errores

    Args:
        log: Log de errores
        max_lines: Máximo de líneas

    Returns:
        Log formateado
    """
    if not log:
        return "No hay errores en el log."

    lines = log.strip().split("\n")
    if len(lines) > max_lines:
        lines = lines[-max_lines:]

    return "\n".join(lines)


def parse_yaml_config(yaml_str: str) -> Dict[str, Any]:
    """
    Parsear configuración YAML

    Args:
        yaml_str: String YAML

    Returns:
        Diccionario con la configuración
    """
    try:
        return yaml.safe_load(yaml_str)
    except yaml.YAMLError as e:
        return {"error": str(e)}


def generate_yaml_config(config: Dict[str, Any]) -> str:
    """
    Generar YAML desde configuración

    Args:
        config: Diccionario de configuración

    Returns:
        String YAML
    """
    return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)