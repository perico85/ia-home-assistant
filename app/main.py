"""
IA Home Assistant - Punto de entrada principal
Asistente IA con control total de Home Assistant usando Ollama Cloud
"""

import os
import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

# Configurar logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__,
            static_folder='../frontend/static',
            template_folder='../frontend')

# Configuración
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['HA_URL'] = os.getenv('HA_URL', 'http://homeassistant:8123')
app.config['HA_TOKEN'] = os.getenv('HA_TOKEN', '')
app.config['OLLAMA_API_KEY'] = os.getenv('OLLAMA_API_KEY', '')
app.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'llama3.2')
app.config['OLLAMA_BASE_URL'] = os.getenv('OLLAMA_BASE_URL', 'https://api.ollama.ai')
app.config['LANGUAGE'] = os.getenv('LANGUAGE', 'es')
app.config['SECURITY_MODE'] = os.getenv('SECURITY_MODE', 'hybrid')

# CORS
CORS(app)

# SocketIO para WebSocket
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Importar módulos después de crear app para evitar imports circulares
from app.core import ollama_client, ha_api, context, executor
from app.interfaces import chat, voice, cli, rest_api
from app.tools import entity_tools, automation, script_tools, config_tools
from app.prompts import system_prompt
from app.utils import logger as app_logger

# Inicializar componentes
ha_client = ha_api.HomeAssistantClient(
    url=app.config['HA_URL'],
    token=app.config['HA_TOKEN']
)

ollama = ollama_client.OllamaClient(
    base_url=app.config['OLLAMA_BASE_URL'],
    api_key=app.config['OLLAMA_API_KEY'],
    model=app.config['OLLAMA_MODEL']
)

context_manager = context.ContextManager(language=app.config['LANGUAGE'])
action_executor = executor.ActionExecutor(ha_client, app.config['SECURITY_MODE'])

# Registrar blueprints
app.register_blueprint(rest_api.bp)

# Configurar WebSocket handlers
chat.setup_socketio(socketio, ollama, ha_client, context_manager, action_executor)

@app.route('/')
def index():
    """Página principal del chat"""
    return app.send_static_file('index.html')

@app.route('/health')
def health():
    """Endpoint de salud"""
    return {'status': 'ok', 'version': '1.0.0'}

def main():
    """Función principal"""
    logger.info("=" * 50)
    logger.info("IA Home Assistant v1.0.0")
    logger.info("=" * 50)
    logger.info(f"Home Assistant URL: {app.config['HA_URL']}")
    logger.info(f"Ollama Model: {app.config['OLLAMA_MODEL']}")
    logger.info(f"Language: {app.config['LANGUAGE']}")
    logger.info(f"Security Mode: {app.config['SECURITY_MODE']}")
    logger.info("=" * 50)

    # Verificar conexiones
    logger.info("Verificando conexiones...")

    # Verificar Home Assistant
    if ha_client.test_connection():
        logger.info("✅ Conexión a Home Assistant: OK")
    else:
        logger.warning("❌ No se pudo conectar a Home Assistant")

    # Verificar Ollama
    if ollama.test_connection():
        logger.info(f"✅ Conexión a Ollama: OK (modelo: {app.config['OLLAMA_MODEL']})")
    else:
        logger.warning("❌ No se pudo conectar a Ollama")

    # Iniciar servidor
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Servidor iniciado en http://{host}:{port}")
    logger.info("Presiona Ctrl+C para detener")

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()