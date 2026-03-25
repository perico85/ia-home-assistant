"""
Interfaz de Chat WebSocket para el asistente IA
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from flask_socketio import SocketIO, emit

logger = logging.getLogger(__name__)

# Referencias globales (se inicializan en setup_socketio)
socketio = None
ollama_client = None
ha_client = None
context_manager = None
action_executor = None


def setup_socketio(
    sio: SocketIO,
    ollama,
    ha,
    context,
    executor
):
    """
    Configurar WebSocket para chat

    Args:
        sio: Instancia de SocketIO
        ollama: Cliente de Ollama
        ha: Cliente de Home Assistant
        context: Gestor de contexto
        executor: Ejecutor de acciones
    """
    global socketio, ollama_client, ha_client, context_manager, action_executor

    socketio = sio
    ollama_client = ollama
    ha_client = ha
    context_manager = context
    action_executor = executor

    # Registrar eventos
    @sio.on('connect')
    def handle_connect():
        logger.info('Cliente conectado')
        emit('connected', {'status': 'ok', 'message': 'Conectado al asistente'})

    @sio.on('disconnect')
    def handle_disconnect():
        logger.info('Cliente desconectado')

    @sio.on('message')
    async def handle_message(data):
        """Manejar mensaje del usuario"""
        await process_user_message(data)

    @sio.on('execute')
    async def handle_execute(data):
        """Ejecutar acción directamente"""
        await execute_action(data)

    @sio.on('change_model')
    def handle_change_model(data):
        """Cambiar modelo de IA"""
        model = data.get('model')
        if model:
            ollama_client.set_model(model)
            emit('model_changed', {'model': model})
        else:
            emit('error', {'message': 'Modelo no especificado'})

    @sio.on('get_history')
    def handle_get_history():
        """Obtener historial de conversación"""
        history = list(context_manager.conversation_history)
        emit('history', {'messages': history})

    @sio.on('clear_history')
    def handle_clear_history():
        """Limpiar historial"""
        context_manager.clear_history()
        emit('history_cleared', {'status': 'ok'})

    @sio.on('get_entities')
    async def handle_get_entities(data):
        """Obtener entidades filtradas"""
        domain = data.get('domain')
        area = data.get('area')

        entities = await ha_client.get_entities(domain=domain, area=area)
        emit('entities', {'entities': entities, 'count': len(entities)})

    @sio.on('confirm_action')
    async def handle_confirm_action(data):
        """Confirmar y ejecutar acción pendiente"""
        action = data.get('action')
        if action:
            result = await action_executor.confirm_and_execute(action)
            emit('action_result', result)
        else:
            emit('error', {'message': 'Acción no especificada'})


async def process_user_message(data: Dict[str, Any]):
    """
    Procesar mensaje del usuario

    Args:
        data: Datos del mensaje {'message': str, 'context': dict}
    """
    user_message = data.get('message', '')
    session_id = data.get('session_id', 'default')

    logger.info(f"Mensaje recibido: {user_message}")

    try:
        # Añadir mensaje al contexto
        context_manager.add_message('user', user_message)

        # Obtener contexto actualizado
        entities = await ha_client.get_states()
        context_manager.update_entity_context({
            e['entity_id']: e for e in entities[:100]  # Limitar para rendimiento
        })

        # Construir mensajes para el LLM
        from app.tools.entity_tools import get_tool_definitions
        from app.tools.automation import get_automation_tools
        from app.tools.script_tools import get_script_tools
        from app.tools.config_tools import get_config_tools

        # Combinar todas las herramientas
        all_tools = (
            get_tool_definitions() +
            get_automation_tools() +
            get_script_tools() +
            get_config_tools()
        )

        # Obtener mensajes formateados
        messages = context_manager.get_messages_for_llm()

        # Añadir prompt del sistema
        from app.prompts.system_prompt import get_system_prompt
        system_prompt = get_system_prompt(
            language=context_manager.language,
            system_context=context_manager._build_system_context()
        )

        # Insertar prompt del sistema al inicio
        messages.insert(0, {"role": "system", "content": system_prompt})

        # Enviar estado de "pensando"
        socketio.emit('thinking', {'status': 'processing'})

        # Llamar a Ollama con streaming
        response_text = ""
        tool_calls = []

        async for chunk in ollama_client.chat_stream(messages, tools=all_tools):
            response_text += chunk
            socketio.emit('stream', {'chunk': chunk})

        # Verificar si hay tool calls en la respuesta
        # (Ollama devuelve tool calls de forma diferente que OpenAI)
        # Por ahora, procesamos el texto y buscamos comandos

        # Buscar comandos en la respuesta
        actions_to_execute = extract_actions_from_response(response_text)

        if actions_to_execute:
            for action in actions_to_execute:
                result = await action_executor.execute(action)

                if result.get('requires_confirmation'):
                    socketio.emit('action_requires_confirmation', {
                        'action': action,
                        'message': result.get('message')
                    })
                else:
                    socketio.emit('action_executed', result)

                    # Añadir resultado al contexto
                    if result.get('success'):
                        context_manager.add_message(
                            'assistant',
                            f"Acción ejecutada: {action['name']}",
                            {'result': result}
                        )

        # Guardar respuesta
        context_manager.add_message('assistant', response_text)

        # Enviar respuesta completa
        socketio.emit('response', {
            'message': response_text,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error procesando mensaje: {e}")
        socketio.emit('error', {'message': str(e)})


async def execute_action(data: Dict[str, Any]):
    """
    Ejecutar acción directamente

    Args:
        data: Datos de la acción {'name': str, 'params': dict}
    """
    action_name = data.get('name')
    params = data.get('params', {})

    logger.info(f"Ejecutando acción: {action_name} con params: {params}")

    try:
        result = await action_executor.execute({
            'name': action_name,
            'params': params
        })

        if result.get('requires_confirmation'):
            socketio.emit('action_requires_confirmation', {
                'action': {'name': action_name, 'params': params},
                'message': result.get('message')
            })
        else:
            socketio.emit('action_result', result)

    except Exception as e:
        logger.error(f"Error ejecutando acción: {e}")
        socketio.emit('error', {'message': str(e)})


def extract_actions_from_response(response: str) -> list:
    """
    Extraer acciones de la respuesta del modelo

    Args:
        response: Texto de respuesta del modelo

    Returns:
        Lista de acciones a ejecutar
    """
    # El modelo puede incluir acciones en formato JSON
    # Buscar patrones como: {"action": "turn_on", "params": {...}}
    import re

    actions = []

    # Buscar bloques JSON
    json_pattern = r'\{[^{}]*"action"\s*:\s*"[^"]+[^{}]*\}'
    matches = re.findall(json_pattern, response)

    for match in matches:
        try:
            action_data = json.loads(match)
            if 'action' in action_data:
                actions.append({
                    'name': action_data['action'],
                    'params': action_data.get('params', {})
                })
        except json.JSONDecodeError:
            continue

    return actions