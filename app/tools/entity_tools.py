"""
Herramientas de control de entidades para el asistente IA
Define las funciones disponibles para el function calling
"""

from typing import Dict, Any, List, Optional


def get_tool_definitions() -> List[Dict[str, Any]]:
    """
    Obtener definiciones de herramientas para el modelo IA
    Formato compatible con Ollama function calling
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "get_entities",
                "description": "Obtener lista de entidades de Home Assistant filtradas por dominio, área o tipo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Dominio de la entidad (light, switch, sensor, climate, etc.)",
                            "enum": ["light", "switch", "sensor", "climate", "cover",
                                    "media_player", "camera", "binary_sensor", "input_boolean",
                                    "input_number", "input_select", "input_text", "scene",
                                    "script", "automation", "group", "person", "device_tracker"]
                        },
                        "area": {
                            "type": "string",
                            "description": "Nombre del área o habitación (salon, cocina, dormitorio, etc.)"
                        },
                        "device_class": {
                            "type": "string",
                            "description": "Clase de dispositivo (motion, temperature, humidity, etc.)"
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_state",
                "description": "Obtener el estado actual de una entidad específica",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad (ej: light.salon, sensor.temperatura)"
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "turn_on",
                "description": "Encender una entidad (luz, interruptor, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad a encender"
                        },
                        "brightness": {
                            "type": "integer",
                            "description": "Brillo para luces (0-255)",
                            "minimum": 0,
                            "maximum": 255
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "turn_off",
                "description": "Apagar una entidad (luz, interruptor, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad a apagar"
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "toggle",
                "description": "Alternar el estado de una entidad (encender si está apagada, apagar si está encendida)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad a alternar"
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "set_value",
                "description": "Establecer un valor en una entidad (brillo, temperatura, volumen, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad"
                        },
                        "value": {
                            "type": ["number", "string"],
                            "description": "Valor a establecer"
                        }
                    },
                    "required": ["entity_id", "value"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "call_service",
                "description": "Llamar a cualquier servicio de Home Assistant",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Dominio del servicio (light, switch, climate, etc.)"
                        },
                        "service": {
                            "type": "string",
                            "description": "Nombre del servicio (turn_on, turn_off, toggle, etc.)"
                        },
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad objetivo (opcional para algunos servicios)"
                        },
                        "data": {
                            "type": "object",
                            "description": "Datos adicionales del servicio"
                        }
                    },
                    "required": ["domain", "service"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_areas",
                "description": "Obtener lista de todas las áreas/estancias de la casa",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_entities",
                "description": "Buscar entidades por nombre o atributo",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Texto a buscar en el nombre o atributos de la entidad"
                        },
                        "domain": {
                            "type": "string",
                            "description": "Filtrar por dominio opcional"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_history",
                "description": "Obtener historial de estados de una entidad",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID de la entidad"
                        },
                        "hours": {
                            "type": "integer",
                            "description": "Horas de historial a obtener (default: 24)",
                            "default": 24
                        }
                    },
                    "required": ["entity_id"]
                }
            }
        }
    ]


def format_entity_for_response(entity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formatear entidad para respuesta al usuario

    Args:
        entity: Datos de la entidad

    Returns:
        Entidad formateada
    """
    attrs = entity.get("attributes", {})
    return {
        "entity_id": entity.get("entity_id"),
        "state": entity.get("state"),
        "name": attrs.get("friendly_name", entity.get("entity_id")),
        "device_class": attrs.get("device_class"),
        "area": attrs.get("area_id"),
        "unit_of_measurement": attrs.get("unit_of_measurement"),
        "last_changed": entity.get("last_changed")
    }


def format_entities_list(entities: List[Dict[str, Any]]) -> str:
    """
    Formatear lista de entidades como texto legible

    Args:
        entities: Lista de entidades

    Returns:
        Texto formateado
    """
    if not entities:
        return "No se encontraron entidades."

    lines = []
    for entity in entities:
        formatted = format_entity_for_response(entity)
        state_str = f"[{formatted['state']}]"
        name = formatted["name"] or formatted["entity_id"]
        lines.append(f"- {name} {state_str}")

    return "\n".join(lines)


def parse_entity_from_text(text: str, entities: List[Dict[str, Any]]) -> Optional[str]:
    """
    Intentar identificar una entidad a partir de texto natural

    Args:
        text: Texto del usuario (ej: "luz del salón", "la de la cocina")
        entities: Lista de entidades disponibles

    Returns:
        entity_id si se encuentra, None si no
    """
    text_lower = text.lower().strip()

    # Buscar por nombre exacto en friendly_name
    for entity in entities:
        attrs = entity.get("attributes", {})
        name = attrs.get("friendly_name", "").lower()
        entity_id = entity.get("entity_id", "").lower()

        # Coincidencia exacta
        if text_lower == name or text_lower == entity_id:
            return entity.get("entity_id")

        # Coincidencia parcial
        if text_lower in name or text_lower in entity_id:
            return entity.get("entity_id")

        # Buscar por palabras clave
        words = text_lower.split()
        if all(word in name or word in entity_id for word in words):
            return entity.get("entity_id")

    return None