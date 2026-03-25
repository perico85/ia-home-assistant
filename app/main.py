"""
IA Home Assistant - Punto de entrada principal
Asistente IA con control total de Home Assistant usando Ollama Cloud
"""

import os
import json
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

# Leer opciones de Home Assistant desde /data/options.json
def load_options():
    """Cargar opciones desde /data/options.json o variables de entorno"""
    options = {
        'ha_url': os.getenv('HA_URL', 'http://homeassistant:8123'),
        'ha_token': os.getenv('HA_TOKEN', ''),
        'ollama_mode': os.getenv('OLLAMA_MODE', 'cloud'),
        'ollama_api_key': os.getenv('OLLAMA_API_KEY', ''),
        'ollama_model': os.getenv('OLLAMA_MODEL', 'llama3.2'),
        'ollama_base_url': os.getenv('OLLAMA_BASE_URL', ''),
        'language': os.getenv('LANGUAGE', 'es'),
        'security_mode': os.getenv('SECURITY_MODE', 'hybrid'),
        'log_level': os.getenv('LOG_LEVEL', 'INFO'),
    }

    # Intentar leer desde /data/options.json (formato Home Assistant Supervisor)
    options_file = '/data/options.json'
    if os.path.exists(options_file):
        try:
            with open(options_file, 'r') as f:
                ha_options = json.load(f)
                logger.info(f"Opciones cargadas desde {options_file}")
                # Sobrescribir con las opciones del usuario
                for key, value in ha_options.items():
                    if key in options:
                        options[key] = value
                        # También exportar como variable de entorno
                        os.environ[key.upper()] = str(value) if value else ''
        except Exception as e:
            logger.warning(f"Error leyendo {options_file}: {e}")
    else:
        logger.info(f"Archivo {options_file} no encontrado, usando variables de entorno")

    return options

# Cargar opciones
options = load_options()

# Crear aplicación Flask
app = Flask(__name__,
            static_folder='../frontend/static',
            template_folder='../frontend')

# Configuración desde opciones
app.config['SECRET_KEY'] = os.urandom(24).hex()
app.config['HA_URL'] = options['ha_url']
app.config['HA_TOKEN'] = options['ha_token']
app.config['OLLAMA_MODE'] = options['ollama_mode']
app.config['OLLAMA_API_KEY'] = options['ollama_api_key']
app.config['OLLAMA_MODEL'] = options['ollama_model']
app.config['OLLAMA_BASE_URL'] = options['ollama_base_url']
app.config['LANGUAGE'] = options['language']
app.config['SECURITY_MODE'] = options['security_mode']

# CORS
CORS(app)

# SocketIO para WebSocket
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Importar módulos después de crear app para evitar imports circulares
from app.core import ollama_client, ollama_cloud_client, ha_api, context, executor
from app.interfaces import chat, voice, cli, rest_api
from app.tools import entity_tools, automation, script_tools, config_tools
from app.prompts import system_prompt
from app.utils import logger as app_logger

# Inicializar componentes
ha_client = ha_api.HomeAssistantClient(
    url=app.config['HA_URL'],
    token=app.config['HA_TOKEN']
)

# Seleccionar cliente Ollama según el modo
if app.config['OLLAMA_MODE'] == 'cloud' or ':cloud' in app.config['OLLAMA_MODEL']:
    # Para Ollama Cloud, usar URL por defecto si no se especifica
    cloud_url = app.config['OLLAMA_BASE_URL'] if app.config['OLLAMA_BASE_URL'] else 'https://ollama.com'
    ollama = ollama_cloud_client.OllamaCloudClient(
        model=app.config['OLLAMA_MODEL'],
        api_key=app.config['OLLAMA_API_KEY'],
        base_url=cloud_url,
        use_cloud=True
    )
    logger.info(f"Usando Ollama Cloud en {cloud_url}")
else:
    local_url = app.config['OLLAMA_BASE_URL'] if app.config['OLLAMA_BASE_URL'] else 'http://localhost:11434'
    ollama = ollama_client.OllamaClient(
        base_url=local_url,
        model=app.config['OLLAMA_MODEL']
    )
    logger.info(f"Usando Ollama local en {local_url}")

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
    logger.info(f"Ollama Mode: {app.config['OLLAMA_MODE']}")
    logger.info(f"Ollama Model: {app.config['OLLAMA_MODEL']}")
    logger.info(f"Language: {app.config['LANGUAGE']}")
    logger.info(f"Security Mode: {app.config['SECURITY_MODE']}")
    logger.info("=" * 50)

    # Verificar que el token está configurado
    if not app.config['HA_TOKEN']:
        logger.error("❌ HA_TOKEN no está configurado!")
        logger.error("   Configure el token de acceso de larga duración en las opciones del add-on")
    else:
        logger.info(f"✅ Token configurado ({len(app.config['HA_TOKEN'])} caracteres)")

    # Verificar conexiones
    logger.info("Verificando conexiones...")

    # Verificar Home Assistant
    if ha_client.test_connection():
        logger.info("✅ Conexión a Home Assistant: OK")
    else:
        logger.warning("❌ No se pudo conectar a Home Assistant - Verifique URL y Token")

    # Verificar Ollama (solo para modo local)
    if app.config['OLLAMA_MODE'] == 'local':
        if hasattr(ollama, 'test_connection') and ollama.test_connection():
            logger.info(f"✅ Conexión a Ollama: OK (modelo: {app.config['OLLAMA_MODEL']})")
        else:
            logger.warning("❌ No se pudo conectar a Ollama")
    else:
        # Para cloud, verificar que hay API key
        if app.config['OLLAMA_API_KEY']:
            logger.info(f"✅ Ollama Cloud configurado (modelo: {app.config['OLLAMA_MODEL']})")
        else:
            logger.warning("⚠️ Ollama Cloud sin API key configurada")

    # Iniciar servidor
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')

    logger.info(f"Servidor iniciado en http://{host}:{port}")
    logger.info("Presiona Ctrl+C para detener")

    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    main()