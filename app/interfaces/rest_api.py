"""
API REST para el asistente IA
Proporciona endpoints HTTP para interactuar con el asistente
"""

import logging
from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Blueprint de Flask
bp = Blueprint('rest_api', __name__, url_prefix='/api')

# Referencias globales (se inicializan desde main.py)
ollama_client = None
ha_client = None
context_manager = None
action_executor = None


def init_api(ollama, ha, context, executor):
    """
    Inicializar API con las referencias necesarias

    Args:
        ollama: Cliente de Ollama
        ha: Cliente de Home Assistant
        context: Gestor de contexto
        executor: Ejecutor de acciones
    """
    global ollama_client, ha_client, context_manager, action_executor
    ollama_client = ollama
    ha_client = ha
    context_manager = context
    action_executor = executor


@bp.route('/status', methods=['GET'])
def get_status():
    """Obtener estado del sistema"""
    return jsonify({
        'status': 'ok',
        'ollama': {
            'model': ollama_client.model,
            'connected': ollama_client.test_connection()
        },
        'homeassistant': {
            'url': ha_client.url,
            'connected': ha_client.test_connection()
        },
        'context': {
            'messages': len(context_manager.conversation_history),
            'language': context_manager.language
        }
    })


@bp.route('/chat', methods=['POST'])
async def chat():
    """
    Enviar mensaje al asistente

    Body JSON:
        {
            "message": "string",
            "session_id": "string (opcional)",
            "context": {} (opcional)
        }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'message es requerido'}), 400

    message = data['message']
    session_id = data.get('session_id', 'default')

    try:
        # Añadir al contexto
        context_manager.add_message('user', message)

        # Obtener contexto actualizado
        entities = await ha_client.get_states()
        context_manager.update_entity_context({
            e['entity_id']: e for e in entities[:50]
        })

        # Construir mensajes
        from app.tools.entity_tools import get_tool_definitions
        from app.prompts.system_prompt import get_system_prompt

        tools = get_tool_definitions()
        messages = context_manager.get_messages_for_llm()

        system_prompt = get_system_prompt(
            language=context_manager.language,
            system_context=context_manager._build_system_context()
        )
        messages.insert(0, {"role": "system", "content": system_prompt})

        # Llamar a Ollama
        response = await ollama_client.chat(messages, tools=tools)

        if response.get('success'):
            content = response.get('message', {}).get('content', '')
            context_manager.add_message('assistant', content)
            return jsonify({
                'success': True,
                'response': content,
                'model': response.get('model')
            })
        else:
            return jsonify({
                'success': False,
                'error': response.get('error', 'Error desconocido')
            }), 500

    except Exception as e:
        logger.error(f"Error en chat: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/chat/stream', methods=['POST'])
async def chat_stream():
    """
    Enviar mensaje con streaming de respuesta
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'error': 'message es requerido'}), 400

    message = data['message']

    def generate():
        context_manager.add_message('user', message)

        from app.prompts.system_prompt import get_system_prompt

        messages = context_manager.get_messages_for_llm()
        system_prompt = get_system_prompt(
            language=context_manager.language,
            system_context=context_manager._build_system_context()
        )
        messages.insert(0, {"role": "system", "content": system_prompt})

        import asyncio

        async def stream_response():
            full_response = ""
            async for chunk in ollama_client.chat_stream(messages):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            context_manager.add_message('assistant', full_response)
            yield "data: [DONE]\n\n"

        # Ejecutar en el event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for chunk in loop.run_until_complete(stream_response()):
            yield chunk

    return Response(generate(), mimetype='text/event-stream')


@bp.route('/entities', methods=['GET'])
async def get_entities():
    """
    Obtener entidades

    Query params:
        domain: Filtrar por dominio
        area: Filtrar por área
    """
    domain = request.args.get('domain')
    area = request.args.get('area')

    try:
        entities = await ha_client.get_entities(domain=domain, area=area)
        return jsonify({
            'success': True,
            'entities': entities,
            'count': len(entities)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>', methods=['GET'])
async def get_entity_state(entity_id: str):
    """Obtener estado de una entidad"""
    try:
        state = await ha_client.get_state(entity_id)
        if state:
            return jsonify({
                'success': True,
                'entity': state
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Entidad no encontrada'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>/turn_on', methods=['POST'])
async def turn_on_entity(entity_id: str):
    """Encender entidad"""
    data = request.get_json() or {}
    brightness = data.get('brightness')

    try:
        result = await action_executor.execute({
            'name': 'turn_on',
            'params': {
                'entity_id': entity_id,
                'brightness': brightness
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>/turn_off', methods=['POST'])
async def turn_off_entity(entity_id: str):
    """Apagar entidad"""
    try:
        result = await action_executor.execute({
            'name': 'turn_off',
            'params': {'entity_id': entity_id}
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/service', methods=['POST'])
async def call_service():
    """
    Llamar servicio de Home Assistant

    Body JSON:
        {
            "domain": "string",
            "service": "string",
            "entity_id": "string (opcional)",
            "data": {} (opcional)
        }
    """
    data = request.get_json()

    if not data or 'domain' not in data or 'service' not in data:
        return jsonify({'error': 'domain y service son requeridos'}), 400

    try:
        result = await action_executor.execute({
            'name': 'call_service',
            'params': {
                'domain': data['domain'],
                'service': data['service'],
                'entity_id': data.get('entity_id'),
                'data': data.get('data', {})
            }
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/automations', methods=['GET'])
async def get_automations():
    """Obtener todas las automatizaciones"""
    try:
        automations = await ha_client.get_automations()
        return jsonify({
            'success': True,
            'automations': automations,
            'count': len(automations)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/automations', methods=['POST'])
async def create_automation():
    """
    Crear automatización

    Body JSON:
        {
            "name": "string",
            "triggers": [],
            "conditions": [] (opcional),
            "actions": []
        }
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Datos requeridos'}), 400

    try:
        from app.tools.automation import build_automation_config

        config = build_automation_config(
            name=data.get('name', 'Nueva automatización'),
            triggers=data.get('triggers', []),
            actions=data.get('actions', []),
            conditions=data.get('conditions'),
            description=data.get('description', '')
        )

        result = await action_executor.execute({
            'name': 'create_automation',
            'params': {'config': config}
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/automations/<automation_id>', methods=['DELETE'])
async def delete_automation(automation_id: str):
    """Eliminar automatización"""
    try:
        result = await action_executor.execute({
            'name': 'delete_automation',
            'params': {'automation_id': automation_id}
        })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/history', methods=['GET'])
def get_conversation_history():
    """Obtener historial de conversación"""
    limit = request.args.get('limit', 50, type=int)

    history = list(context_manager.conversation_history)[-limit:]

    return jsonify({
        'success': True,
        'history': history,
        'count': len(history)
    })


@bp.route('/history', methods=['DELETE'])
def clear_conversation_history():
    """Limpiar historial de conversación"""
    context_manager.clear_history()
    return jsonify({'success': True, 'message': 'Historial limpiado'})


@bp.route('/model', methods=['GET'])
def get_model():
    """Obtener modelo actual"""
    return jsonify({
        'model': ollama_client.model
    })


@bp.route('/model', methods=['PUT'])
def set_model():
    """Cambiar modelo"""
    data = request.get_json()

    if not data or 'model' not in data:
        return jsonify({'error': 'model es requerido'}), 400

    model = data['model']
    ollama_client.set_model(model)

    return jsonify({
        'success': True,
        'model': model
    })


@bp.route('/logs', methods=['GET'])
async def get_action_logs():
    """Obtener log de acciones"""
    limit = request.args.get('limit', 100, type=int)

    logs = action_executor.get_action_log(limit=limit)

    return jsonify({
        'success': True,
        'logs': logs,
        'count': len(logs)
    })


@bp.route('/rollback', methods=['POST'])
async def rollback_last_action():
    """Deshacer última acción"""
    result = await action_executor.rollback_last()
    return jsonify(result)