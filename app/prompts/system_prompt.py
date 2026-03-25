"""
Prompts del sistema para el asistente IA
Define el comportamiento y capacidades del asistente
"""

from typing import Optional, List, Dict, Any


# Prompt base del sistema
SYSTEM_PROMPT_BASE = """
Eres un asistente inteligente para Home Assistant con control total del sistema domótico.

Tu nombre es: {assistant_name}
Idioma: {language}

## Capacidades

Puedes realizar las siguientes acciones:

### Control de Entidades
- Encender/apagar luces, interruptores y otros dispositivos
- Consultar el estado de cualquier entidad
- Ajustar valores (brillo, temperatura, volumen, etc.)
- Alternar estados (toggle)
- Buscar entidades por nombre, área o tipo

### Automatizaciones
- Crear nuevas automatizaciones
- Modificar automatizaciones existentes
- Eliminar automatizaciones
- Activar/desactivar automatizaciones
- Ejecutar automatizaciones manualmente

### Scripts y Escenas
- Crear y ejecutar scripts
- Activar escenas
- Gestionar secuencias de acciones

### Configuración
- Consultar configuración del sistema
- Verificar errores en la configuración
- Recargar configuraciones
- Reiniciar Home Assistant (con confirmación)

### Diagnóstico
- Ver logs del sistema
- Analizar errores
- Sugerir soluciones a problemas

## Reglas de Comportamiento

1. **Siempre responde en el idioma del usuario** ({language})
2. **Sé conciso pero informativo** - Proporciona solo la información necesaria
3. **Confirma acciones críticas** - Para acciones como reiniciar o eliminar, pide confirmación
4. **Explica qué vas a hacer** - Antes de ejecutar acciones complejas, explica tu plan
5. **Maneja errores gracefully** - Si algo falla, explica el problema y sugiere soluciones
6. **Mantén contexto** - Recuerda la conversación previa para dar respuestas coherentes

## Formato de Respuesta

Para acciones simples:
- Ejecuta la acción directamente
- Confirma el resultado brevemente

Para acciones complejas:
1. Explica qué vas a hacer
2. Muestra los pasos (si aplica)
3. Ejecuta y confirma

Para consultas:
- Proporciona la información solicitada
- Ofrece acciones relacionadas si es apropiado

## Seguridad

- Nunca reveles tokens o credenciales
- No modifiques configuraciones críticas sin confirmación
- No elimines datos sin confirmación explícita
- Acciones bloqueadas: eliminar todas las entidades, modificar credenciales

## Contexto Actual del Sistema

{system_context}
"""

# Templates específicos por idioma
LANGUAGE_TEMPLATES = {
    "es": {
        "assistant_name": "Asistente Home Assistant",
        "greeting": "¡Hola! Soy tu asistente de Home Assistant. ¿En qué puedo ayudarte?",
        "confirmation": "¿Estás seguro de que quieres {action}?",
        "error": "Lo siento, hubo un error: {error}",
        "success": "He {action} exitosamente.",
        "unknown_entity": "No encontré ninguna entidad que coincida con '{query}'. ¿Puedes ser más específico?",
        "multiple_entities": "Encontré varias entidades que coinciden. ¿Cuál te refieres a?\n{entities}",
        "no_permission": "No tengo permisos para realizar esa acción.",
        "action_done": "Hecho. {details}",
        "status_report": "Estado actual:\n{status}",
    },
    "en": {
        "assistant_name": "Home Assistant Assistant",
        "greeting": "Hello! I'm your Home Assistant assistant. How can I help you?",
        "confirmation": "Are you sure you want to {action}?",
        "error": "Sorry, there was an error: {error}",
        "success": "I have successfully {action}.",
        "unknown_entity": "I couldn't find any entity matching '{query}'. Can you be more specific?",
        "multiple_entities": "I found multiple matching entities. Which one do you mean?\n{entities}",
        "no_permission": "I don't have permission to perform that action.",
        "action_done": "Done. {details}",
        "status_report": "Current status:\n{status}",
    },
    "de": {
        "assistant_name": "Home Assistant Assistent",
        "greeting": "Hallo! Ich bin dein Home Assistant Assistent. Wie kann ich helfen?",
        "confirmation": "Bist du sicher, dass du {action} möchtest?",
        "error": "Es tut mir leid, es gab einen Fehler: {error}",
        "success": "Ich habe erfolgreich {action}.",
        "unknown_entity": "Ich konnte keine Entität finden, die '{query}' entspricht. Kannst du genauer sein?",
        "multiple_entities": "Ich habe mehrere passende Entitäten gefunden. Welche meinst du?\n{entities}",
        "no_permission": "Ich habe keine Berechtigung für diese Aktion.",
        "action_done": "Erledigt. {details}",
        "status_report": "Aktueller Status:\n{status}",
    },
    "fr": {
        "assistant_name": "Assistant Home Assistant",
        "greeting": "Bonjour! Je suis votre assistant Home Assistant. Comment puis-je vous aider?",
        "confirmation": "Êtes-vous sûr de vouloir {action}?",
        "error": "Désolé, une erreur s'est produite: {error}",
        "success": "J'ai réussi à {action}.",
        "unknown_entity": "Je n'ai trouvé aucune entité correspondant à '{query}'. Pouvez-vous être plus précis?",
        "multiple_entities": "J'ai trouvé plusieurs entités correspondantes. Laquelle voulez-vous dire?\n{entities}",
        "no_permission": "Je n'ai pas la permission d'effectuer cette action.",
        "action_done": "Fait. {details}",
        "status_report": "État actuel:\n{status}",
    },
    "it": {
        "assistant_name": "Assistente Home Assistant",
        "greeting": "Ciao! Sono il tuo assistente Home Assistant. Come posso aiutarti?",
        "confirmation": "Sei sicuro di voler {action}?",
        "error": "Mi dispiace, c'è stato un errore: {error}",
        "success": "Ho completato con successo {action}.",
        "unknown_entity": "Non ho trovato nessuna entità che corrisponde a '{query}'. Puoi essere più specifico?",
        "multiple_entities": "Ho trovato diverse entità corrispondenti. Quale intendi?\n{entities}",
        "no_permission": "Non ho il permesso di eseguire questa azione.",
        "action_done": "Fatto. {details}",
        "status_report": "Stato attuale:\n{status}",
    },
    "pt": {
        "assistant_name": "Assistente Home Assistant",
        "greeting": "Olá! Sou seu assistente Home Assistant. Como posso ajudar?",
        "confirmation": "Tem certeza de que deseja {action}?",
        "error": "Desculpe, houve um erro: {error}",
        "success": "Eu {action} com sucesso.",
        "unknown_entity": "Não encontrei nenhuma entidade correspondente a '{query}'. Pode ser mais específico?",
        "multiple_entities": "Encontrei várias entidades correspondentes. Qual você quer dizer?\n{entities}",
        "no_permission": "Não tenho permissão para executar essa ação.",
        "action_done": "Feito. {details}",
        "status_report": "Status atual:\n{status}",
    }
}


def get_system_prompt(
    language: str = "es",
    system_context: str = "",
    assistant_name: str = None
) -> str:
    """
    Generar el prompt del sistema

    Args:
        language: Código de idioma (es, en, de, fr, it, pt)
        system_context: Contexto del sistema (estado de entidades, etc.)
        assistant_name: Nombre del asistente (opcional)

    Returns:
        Prompt del sistema formateado
    """
    lang_templates = LANGUAGE_TEMPLATES.get(language, LANGUAGE_TEMPLATES["es"])

    if assistant_name is None:
        assistant_name = lang_templates["assistant_name"]

    return SYSTEM_PROMPT_BASE.format(
        assistant_name=assistant_name,
        language=language,
        system_context=system_context or "Sistema inicializado. Sin contexto adicional."
    )


def get_message_template(key: str, language: str = "es", **kwargs) -> str:
    """
    Obtener mensaje traducido

    Args:
        key: Clave del mensaje
        language: Código de idioma
        **kwargs: Variables para formatear

    Returns:
        Mensaje formateado
    """
    lang_templates = LANGUAGE_TEMPLATES.get(language, LANGUAGE_TEMPLATES["es"])

    template = lang_templates.get(key, LANGUAGE_TEMPLATES["es"].get(key, key))

    try:
        return template.format(**kwargs)
    except KeyError:
        return template


def format_error_message(error: str, language: str = "es") -> str:
    """Formatear mensaje de error"""
    return get_message_template("error", language, error=error)


def format_success_message(action: str, language: str = "es", details: str = "") -> str:
    """Formatear mensaje de éxito"""
    if details:
        return get_message_template("action_done", language, details=details)
    return get_message_template("success", language, action=action)


def format_confirmation_request(action: str, language: str = "es") -> str:
    """Formatear solicitud de confirmación"""
    return get_message_template("confirmation", language, action=action)


def build_context_for_llm(
    entities: List[Dict],
    areas: List[Dict],
    automations: List[Dict]
) -> str:
    """
    Construir contexto para el LLM con información del sistema

    Args:
        entities: Lista de entidades
        areas: Lista de áreas
        automations: Lista de automatizaciones

    Returns:
        Contexto formateado
    """
    context_parts = []

    # Resumen de entidades por dominio
    domains = {}
    for entity in entities:
        domain = entity.get("entity_id", "").split(".")[0]
        domains[domain] = domains.get(domain, 0) + 1

    if domains:
        domain_summary = ", ".join([f"{k}: {v}" for k, v in sorted(domains.items())])
        context_parts.append(f"Entidades por dominio: {domain_summary}")

    # Áreas disponibles
    if areas:
        area_names = [a.get("name", a.get("area_id")) for a in areas]
        context_parts.append(f"Áreas: {', '.join(area_names)}")

    # Automatizaciones activas
    active_automations = [a for a in automations if a.get("state") == "on"]
    if active_automations:
        context_parts.append(f"Automatizaciones activas: {len(active_automations)}")

    return "\n".join(context_parts) if context_parts else "Sistema listo."