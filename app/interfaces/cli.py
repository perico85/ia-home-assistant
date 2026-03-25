"""
Interfaz CLI para el asistente IA
Permite interactuar desde la línea de comandos
"""

import asyncio
import logging
import sys
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class CLIInterface:
    """
    Interfaz de línea de comandos para el asistente IA
    """

    def __init__(self, ollama_client, ha_client, context_manager, action_executor):
        """
        Inicializar CLI

        Args:
            ollama_client: Cliente de Ollama
            ha_client: Cliente de Home Assistant
            context_manager: Gestor de contexto
            action_executor: Ejecutor de acciones
        """
        self.ollama = ollama_client
        self.ha = ha_client
        self.context = context_manager
        self.executor = action_executor

        self.running = False
        self.last_result = None

    async def start(self):
        """Iniciar interfaz CLI"""
        self.running = True

        print("\n" + "=" * 50)
        print("IA Home Assistant - Interfaz CLI")
        print("=" * 50)
        print("Escribe 'help' para ver los comandos disponibles.")
        print("Escribe 'exit' o 'quit' para salir.\n")

        while self.running:
            try:
                # Leer entrada del usuario
                user_input = input("Tú: ").strip()

                if not user_input:
                    continue

                # Procesar comando
                if user_input.lower() in ['exit', 'quit', 'salir']:
                    self.running = False
                    print("¡Hasta pronto!")
                    break

                if user_input.lower() == 'help':
                    self._show_help()
                    continue

                if user_input.lower() == 'status':
                    await self._show_status()
                    continue

                if user_input.lower() == 'history':
                    self._show_history()
                    continue

                if user_input.lower() == 'clear':
                    self.context.clear_history()
                    print("Historial limpiado.")
                    continue

                if user_input.lower().startswith('model '):
                    model = user_input[6:].strip()
                    self.ollama.set_model(model)
                    print(f"Modelo cambiado a: {model}")
                    continue

                if user_input.lower().startswith('exec '):
                    command = user_input[5:].strip()
                    await self._execute_command(command)
                    continue

                # Procesar como mensaje al asistente
                await self._process_message(user_input)

            except KeyboardInterrupt:
                print("\nSaliendo...")
                self.running = False
            except Exception as e:
                logger.error(f"Error: {e}")
                print(f"Error: {e}")

    def _show_help(self):
        """Mostrar ayuda"""
        print("""
Comandos disponibles:

  help          - Mostrar esta ayuda
  status        - Mostrar estado del sistema
  history       - Mostrar historial de conversación
  clear         - Limpiar historial
  model <name>  - Cambiar modelo de IA
  exec <cmd>    - Ejecutar comando directo
  exit/quit     - Salir

Comandos directos (exec):
  exec entities [domain]       - Listar entidades
  exec state <entity_id>       - Estado de entidad
  exec on <entity_id>          - Encender entidad
  exec off <entity_id>         - Apagar entidad
  exec toggle <entity_id>      - Alternar entidad
  exec automations             - Listar automatizaciones
  exec logs                    - Ver logs

Ejemplos:
  "Enciende la luz del salón"
  "¿Cuál es la temperatura?"
  "Apaga todas las luces"
  "Crea una automatización para..."
        """)

    async def _show_status(self):
        """Mostrar estado del sistema"""
        print("\nEstado del sistema:")
        print(f"  Modelo: {self.ollama.model}")
        print(f"  Idioma: {self.context.language}")
        print(f"  Modo seguridad: {self.executor.security_mode}")
        print(f"  Mensajes en historial: {len(self.context.conversation_history)}")

        # Verificar conexiones
        ha_ok = self.ha.test_connection()
        ollama_ok = self.ollama.test_connection()

        print(f"  Conexión HA: {'✓' if ha_ok else '✗'}")
        print(f"  Conexión Ollama: {'✓' if ollama_ok else '✗'}")
        print()

    def _show_history(self):
        """Mostrar historial de conversación"""
        print("\nHistorial de conversación:")
        print("-" * 40)

        if not self.context.conversation_history:
            print("(vacío)")
            return

        for msg in self.context.conversation_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            timestamp = msg.get("timestamp", "")

            prefix = "Tú" if role == "user" else "Asistente"
            print(f"[{timestamp}] {prefix}: {content}")

        print()

    async def _process_message(self, message: str):
        """
        Procesar mensaje del usuario

        Args:
            message: Mensaje del usuario
        """
        print("\nProcesando...")

        try:
            # Añadir al contexto
            self.context.add_message("user", message)

            # Obtener contexto actualizado
            entities = await self.ha.get_states()
            self.context.update_entity_context({
                e['entity_id']: e for e in entities[:50]
            })

            # Construir mensajes para el LLM
            from app.tools.entity_tools import get_tool_definitions
            from app.prompts.system_prompt import get_system_prompt

            tools = get_tool_definitions()

            messages = self.context.get_messages_for_llm()

            # Añadir prompt del sistema
            system_prompt = get_system_prompt(
                language=self.context.language,
                system_context=self.context._build_system_context()
            )
            messages.insert(0, {"role": "system", "content": system_prompt})

            # Llamar a Ollama
            response = await self.ollama.chat(messages, tools=tools)

            if response.get("success"):
                content = response.get("message", {}).get("content", "")
                self.context.add_message("assistant", content)
                print(f"\nAsistente: {content}")
            else:
                error = response.get("error", "Error desconocido")
                print(f"\nError: {error}")

        except Exception as e:
            logger.error(f"Error procesando mensaje: {e}")
            print(f"\nError: {e}")

    async def _execute_command(self, command: str):
        """
        Ejecutar comando directo

        Args:
            command: Comando a ejecutar
        """
        parts = command.split()
        if not parts:
            print("Comando vacío")
            return

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd == "entities":
                domain = args[0] if args else None
                entities = await self.ha.get_entities(domain=domain)
                print(f"\nEntidades ({len(entities)}):")
                for e in entities[:20]:
                    name = e.get("attributes", {}).get("friendly_name", e.get("entity_id"))
                    state = e.get("state")
                    print(f"  - {name}: {state}")
                if len(entities) > 20:
                    print(f"  ... y {len(entities) - 20} más")

            elif cmd == "state":
                if not args:
                    print("Uso: exec state <entity_id>")
                    return
                entity_id = args[0]
                state = await self.ha.get_state(entity_id)
                if state:
                    print(f"\n{entity_id}:")
                    print(f"  Estado: {state.get('state')}")
                    attrs = state.get("attributes", {})
                    if attrs:
                        print("  Atributos:")
                        for k, v in list(attrs.items())[:10]:
                            print(f"    {k}: {v}")
                else:
                    print(f"Entidad no encontrada: {entity_id}")

            elif cmd == "on":
                if not args:
                    print("Uso: exec on <entity_id>")
                    return
                entity_id = args[0]
                result = await self.executor.execute({
                    "name": "turn_on",
                    "params": {"entity_id": entity_id}
                })
                print(f"Resultado: {result}")

            elif cmd == "off":
                if not args:
                    print("Uso: exec off <entity_id>")
                    return
                entity_id = args[0]
                result = await self.executor.execute({
                    "name": "turn_off",
                    "params": {"entity_id": entity_id}
                })
                print(f"Resultado: {result}")

            elif cmd == "toggle":
                if not args:
                    print("Uso: exec toggle <entity_id>")
                    return
                entity_id = args[0]
                result = await self.executor.execute({
                    "name": "toggle",
                    "params": {"entity_id": entity_id}
                })
                print(f"Resultado: {result}")

            elif cmd == "automations":
                automations = await self.ha.get_automations()
                print(f"\nAutomatizaciones ({len(automations)}):")
                for a in automations:
                    name = a.get("attributes", {}).get("friendly_name", a.get("entity_id"))
                    state = a.get("state")
                    print(f"  - {name}: {state}")

            elif cmd == "logs":
                logs = await self.ha.get_error_log()
                print("\nLogs de error:")
                print(logs[-2000:] if len(logs) > 2000 else logs)

            else:
                print(f"Comando desconocido: {cmd}")

        except Exception as e:
            print(f"Error ejecutando comando: {e}")


async def run_cli(ollama, ha, context, executor):
    """
    Ejecutar interfaz CLI

    Args:
        ollama: Cliente de Ollama
        ha: Cliente de Home Assistant
        context: Gestor de contexto
        executor: Ejecutor de acciones
    """
    cli = CLIInterface(ollama, ha, context, executor)
    await cli.start()


if __name__ == "__main__":
    # Para pruebas independientes
    print("Para usar el CLI, ejecuta main.py")