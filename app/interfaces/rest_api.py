"""
API REST para el asistente IA
Proporciona endpoints HTTP para interactuar con el asistente
"""

import logging
import asyncio
from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any, List

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
    """
    global ollama_client, ha_client, context_manager, action_executor
    ollama_client = ollama
    ha_client = ha
    context_manager = context
    action_executor = executor


@bp.route('/health', methods=['GET'])
def health():
    """Endpoint de salud para verificar que el addon está funcionando"""
    return jsonify({'status': 'ok', 'version': '1.0.0'})


@bp.route('/status', methods=['GET'])
def get_status():
    """Obtener estado del sistema"""
    try:
        ollama_connected = ollama_client.test_connection() if ollama_client else False
        ha_connected = ha_client.test_connection() if ha_client else False
    except Exception as e:
        logger.error(f"Error verificando conexiones: {e}")
        ollama_connected = False
        ha_connected = False

    return jsonify({
        'status': 'ok',
        'ollama': {
            'model': getattr(ollama_client, 'model', 'unknown') if ollama_client else None,
            'connected': ollama_connected
        },
        'homeassistant': {
            'url': ha_client.url if ha_client else None,
            'connected': ha_connected
        },
        'context': {
            'messages': len(context_manager.conversation_history) if context_manager else 0,
            'language': getattr(context_manager, 'language', 'es') if context_manager else 'es'
        }
    })


@bp.route('/chat', methods=['POST'])
def chat():
    """
    Enviar mensaje al asistente

    Body JSON:
        {
            "message": "string (requerido)",
            "language": "string (opcional, default: es)",
            "context": {
                "entities": [...],
                "conversation_id": "string"
            }
        }

    Returns:
        {
            "success": bool,
            "message": "string (respuesta del asistente)"
        }
    """
    data = request.get_json()

    if not data or 'message' not in data:
        return jsonify({'success': False, 'error': 'message es requerido'}), 400

    message = data['message']
    language = data.get('language', 'es')
    context_data = data.get('context', {})
    entities = context_data.get('entities', [])

    try:
        # Ejecutar de forma síncrona usando asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_process_chat(message, language, entities))
        loop.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


async def _process_chat(message: str, language: str, entities: List[Dict]) -> Dict:
    """Procesar mensaje de chat"""
    # Añadir al contexto
    context_manager.add_message('user', message)

    # Actualizar contexto con entidades proporcionadas
    if entities:
        context_manager.update_entity_context({
            e['entity_id']: e for e in entities
        })
    else:
        # Obtener entidades de Home Assistant si no se proporcionaron
        try:
            ha_entities = await ha_client.get_states()
            context_manager.update_entity_context({
                e['entity_id']: e for e in ha_entities[:50]
            })
        except Exception as e:
            logger.warning(f"No se pudieron obtener entidades: {e}")

    # Construir mensajes para el LLM
    from app.tools.entity_tools import get_tool_definitions
    from app.prompts.system_prompt import get_system_prompt

    tools = get_tool_definitions()
    messages = context_manager.get_messages_for_llm()

    system_prompt = get_system_prompt(
        language=language,
        system_context=context_manager._build_system_context()
    )
    messages.insert(0, {"role": "system", "content": system_prompt})

    # Llamar a Ollama
    response = await ollama_client.chat(messages, tools=tools)

    if response.get('success'):
        content = response.get('message', {}).get('content', '')
        context_manager.add_message('assistant', content)
        return {
            'success': True,
            'message': content,
            'model': response.get('model')
        }
    else:
        return {
            'success': False,
            'error': response.get('error', 'Error desconocido')
        }


@bp.route('/chat/stream', methods=['POST'])
def chat_stream():
    """Enviar mensaje con streaming de respuesta"""
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

        async def stream_response():
            full_response = ""
            async for chunk in ollama_client.chat_stream(messages):
                full_response += chunk
                yield f"data: {chunk}\n\n"

            context_manager.add_message('assistant', full_response)
            yield "data: [DONE]\n\n"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        for chunk in loop.run_until_complete(stream_response()):
            yield chunk

    return Response(generate(), mimetype='text/event-stream')


@bp.route('/entities', methods=['GET'])
def get_entities():
    """Obtener entidades"""
    domain = request.args.get('domain')
    area = request.args.get('area')

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        entities = loop.run_until_complete(ha_client.get_entities(domain=domain, area=area))
        loop.close()
        return jsonify({
            'success': True,
            'entities': entities,
            'count': len(entities)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>', methods=['GET'])
def get_entity_state(entity_id: str):
    """Obtener estado de una entidad"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        state = loop.run_until_complete(ha_client.get_state(entity_id))
        loop.close()
        if state:
            return jsonify({'success': True, 'entity': state})
        else:
            return jsonify({'success': False, 'error': 'Entidad no encontrada'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>/turn_on', methods=['POST'])
def turn_on_entity(entity_id: str):
    """Encender entidad"""
    data = request.get_json() or {}
    brightness = data.get('brightness')

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(action_executor.execute({
            'name': 'turn_on',
            'params': {'entity_id': entity_id, 'brightness': brightness}
        }))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/entities/<entity_id>/turn_off', methods=['POST'])
def turn_off_entity(entity_id: str):
    """Apagar entidad"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(action_executor.execute({
            'name': 'turn_off',
            'params': {'entity_id': entity_id}
        }))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/service', methods=['POST'])
def call_service():
    """Llamar servicio de Home Assistant"""
    data = request.get_json()

    if not data or 'domain' not in data or 'service' not in data:
        return jsonify({'error': 'domain y service son requeridos'}), 400

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(action_executor.execute({
            'name': 'call_service',
            'params': {
                'domain': data['domain'],
                'service': data['service'],
                'entity_id': data.get('entity_id'),
                'data': data.get('data', {})
            }
        }))
        loop.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/history', methods=['GET'])
def get_conversation_history():
    """Obtener historial de conversación"""
    limit = request.args.get('limit', 50, type=int)
    history = list(context_manager.conversation_history)[-limit:]
    return jsonify({'success': True, 'history': history, 'count': len(history)})


@bp.route('/history', methods=['DELETE'])
def clear_conversation_history():
    """Limpiar historial de conversación"""
    context_manager.clear_history()
    return jsonify({'success': True, 'message': 'Historial limpiado'})


@bp.route('/model', methods=['GET'])
def get_model():
    """Obtener modelo actual"""
    return jsonify({'model': ollama_client.model})


@bp.route('/model', methods=['PUT'])
def set_model():
    """Cambiar modelo"""
    data = request.get_json()
    if not data or 'model' not in data:
        return jsonify({'error': 'model es requerido'}), 400

    model = data['model']
    ollama_client.set_model(model)
    return jsonify({'success': True, 'model': model})