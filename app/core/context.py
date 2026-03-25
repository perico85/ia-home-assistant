"""
Gestor de contexto conversacional
Mantiene el historial y contexto de la conversación
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import deque

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Gestiona el contexto de la conversación con el asistente.
    Mantiene historial de mensajes, estado de entidades y información relevante.
    """

    def __init__(
        self,
        language: str = "es",
        max_history: int = 50,
        max_context_tokens: int = 4000
    ):
        self.language = language
        self.max_history = max_history
        self.max_context_tokens = max_context_tokens

        # Historial de conversación
        self.conversation_history: deque = deque(maxlen=max_history)

        # Contexto de Home Assistant
        self.entity_states: Dict[str, Dict] = {}
        self.last_action: Optional[Dict] = None
        self.active_automations: List[str] = []

        # Memoria a corto plazo
        self.short_term_memory: Dict[str, Any] = {}

        # Preferencias del usuario (aprendidas)
        self.user_preferences: Dict[str, Any] = {}

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Añadir mensaje al historial

        Args:
            role: 'user', 'assistant' o 'system'
            content: Contenido del mensaje
            metadata: Metadatos adicionales (acciones ejecutadas, etc.)

        Returns:
            Mensaje añadido
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        self.conversation_history.append(message)
        logger.debug(f"Mensaje añadido: {role} - {content[:50]}...")

        return message

    def get_messages_for_llm(
        self,
        include_system: bool = True,
        max_messages: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Obtener mensajes formateados para el LLM

        Args:
            include_system: Si incluir el prompt del sistema
            max_messages: Número máximo de mensajes

        Returns:
            Lista de mensajes en formato para el LLM
        """
        messages = []

        # Añadir contexto del sistema si está disponible
        if include_system:
            system_context = self._build_system_context()
            if system_context:
                messages.append({
                    "role": "system",
                    "content": system_context
                })

        # Añadir historial de conversación
        history = list(self.conversation_history)
        if max_messages:
            history = history[-max_messages:]

        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        return messages

    def _build_system_context(self) -> str:
        """Construir contexto del sistema para el LLM"""
        context_parts = []

        # Información del idioma
        context_parts.append(f"Idioma: {self.language}")

        # Estado de entidades relevantes
        if self.entity_states:
            entities_context = self._format_entities_context()
            if entities_context:
                context_parts.append(f"\nEntidades actuales:\n{entities_context}")

        # Última acción realizada
        if self.last_action:
            action_str = json.dumps(self.last_action, ensure_ascii=False)
            context_parts.append(f"\nÚltima acción: {action_str}")

        # Preferencias del usuario
        if self.user_preferences:
            prefs_str = json.dumps(self.user_preferences, ensure_ascii=False)
            context_parts.append(f"\nPreferencias del usuario: {prefs_str}")

        return "\n".join(context_parts)

    def _format_entities_context(self) -> str:
        """Formatear contexto de entidades"""
        lines = []
        for entity_id, state in list(self.entity_states.items())[:20]:  # Limitar a 20
            friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
            current_state = state.get("state", "unknown")
            lines.append(f"- {friendly_name} ({entity_id}): {current_state}")
        return "\n".join(lines)

    def update_entity_context(self, entities: Dict[str, Dict]) -> None:
        """Actualizar contexto con estado de entidades"""
        self.entity_states.update(entities)
        logger.debug(f"Contexto actualizado con {len(entities)} entidades")

    def update_last_action(self, action: Dict[str, Any]) -> None:
        """Actualizar última acción ejecutada"""
        self.last_action = {
            "action": action,
            "timestamp": datetime.now().isoformat()
        }

    def set_preference(self, key: str, value: Any) -> None:
        """Establecer preferencia del usuario"""
        self.user_preferences[key] = value
        logger.info(f"Preferencia establecida: {key} = {value}")

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Obtener preferencia del usuario"""
        return self.user_preferences.get(key, default)

    def set_short_term_memory(self, key: str, value: Any) -> None:
        """Establecer valor en memoria a corto plazo"""
        self.short_term_memory[key] = {
            "value": value,
            "timestamp": datetime.now().isoformat()
        }

    def get_short_term_memory(self, key: str) -> Optional[Any]:
        """Obtener valor de memoria a corto plazo"""
        if key in self.short_term_memory:
            return self.short_term_memory[key]["value"]
        return None

    def clear_history(self) -> None:
        """Limpiar historial de conversación"""
        self.conversation_history.clear()
        logger.info("Historial de conversación limpiado")

    def export_context(self) -> Dict[str, Any]:
        """Exportar contexto completo para persistencia"""
        return {
            "language": self.language,
            "conversation_history": list(self.conversation_history),
            "user_preferences": self.user_preferences,
            "export_timestamp": datetime.now().isoformat()
        }

    def import_context(self, data: Dict[str, Any]) -> None:
        """Importar contexto desde datos persistentes"""
        self.language = data.get("language", "es")
        self.user_preferences = data.get("user_preferences", {})

        # Restaurar historial
        for msg in data.get("conversation_history", []):
            self.conversation_history.append(msg)

        logger.info(f"Contexto importado: {len(self.conversation_history)} mensajes")

    def get_summary(self) -> str:
        """Obtener resumen del contexto actual"""
        return f"""
Contexto actual:
- Mensajes en historial: {len(self.conversation_history)}
- Entidades cacheadas: {len(self.entity_states)}
- Preferencias guardadas: {len(self.user_preferences)}
- Idioma: {self.language}
"""