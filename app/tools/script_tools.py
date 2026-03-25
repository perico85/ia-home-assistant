"""
Herramientas de scripts para el asistente IA
"""

from typing import Dict, Any, List, Optional
import yaml


def get_script_tools() -> List[Dict[str, Any]]:
    """Obtener definiciones de herramientas de scripts"""
    return [
        {
            "type": "function",
            "function": {
                "name": "get_scripts",
                "description": "Obtener lista de todos los scripts disponibles",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_script",
                "description": "Ejecutar un script",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {
                            "type": "string",
                            "description": "ID del script a ejecutar"
                        },
                        "variables": {
                            "type": "object",
                            "description": "Variables para el script"
                        }
                    },
                    "required": ["script_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_script",
                "description": "Crear un nuevo script",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre del script"
                        },
                        "sequence": {
                            "type": "array",
                            "description": "Secuencia de acciones del script",
                            "items": {
                                "type": "object"
                            }
                        },
                        "mode": {
                            "type": "string",
                            "description": "Modo de ejecución",
                            "enum": ["single", "restart", "queued", "parallel"]
                        },
                        "max": {
                            "type": "integer",
                            "description": "Máximo de ejecuciones concurrentes"
                        }
                    },
                    "required": ["name", "sequence"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "turn_on_script",
                "description": "Activar un script (para scripts con modo restart)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {
                            "type": "string",
                            "description": "ID del script"
                        }
                    },
                    "required": ["script_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "turn_off_script",
                "description": "Detener un script en ejecución",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "script_id": {
                            "type": "string",
                            "description": "ID del script"
                        }
                    },
                    "required": ["script_id"]
                }
            }
        }
    ]


def build_script_config(
    name: str,
    sequence: List[Dict],
    mode: str = "single",
    max_executions: int = 10,
    description: str = ""
) -> Dict[str, Any]:
    """
    Construir configuración de script

    Args:
        name: Nombre del script
        sequence: Secuencia de acciones
        mode: Modo de ejecución
        max_executions: Máximo de ejecuciones
        description: Descripción

    Returns:
        Configuración del script
    """
    script_id = name.lower().replace(" ", "_").replace("-", "_")

    return {
        "alias": name,
        "description": description,
        "sequence": sequence,
        "mode": mode,
        "max": max_executions
    }


def generate_script_yaml(config: Dict[str, Any], script_id: str) -> str:
    """
    Generar YAML de script

    Args:
        config: Configuración del script
        script_id: ID del script

    Returns:
        YAML formateado
    """
    return yaml.dump({script_id: config}, allow_unicode=True, default_flow_style=False, sort_keys=False)