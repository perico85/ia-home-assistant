"""
Interfaz de Voz para el asistente IA
Soporte para Speech-to-Text y Text-to-Speech
"""

import logging
import speech_recognition as sr
import pyttsx3
from typing import Optional, Callable, Dict, Any
import threading
import queue

logger = logging.getLogger(__name__)


class VoiceInterface:
    """
    Interfaz de voz para interactuar con el asistente
    Soporta reconocimiento de voz y síntesis de voz
    """

    def __init__(
        self,
        language: str = "es-ES",
        tts_enabled: bool = True,
        stt_engine: str = "google"
    ):
        """
        Inicializar interfaz de voz

        Args:
            language: Código de idioma (es-ES, en-US, etc.)
            tts_enabled: Si habilitar text-to-speech
            stt_engine: Motor de speech-to-text (google, sphinx, whisper)
        """
        self.language = language
        self.tts_enabled = tts_enabled
        self.stt_engine = stt_engine

        # Inicializar reconocedor
        self.recognizer = sr.Recognizer()

        # Inicializar TTS
        self.tts_engine = None
        if tts_enabled:
            self._init_tts()

        # Cola de comandos
        self.command_queue = queue.Queue()
        self.is_listening = False

        # Callback para comandos
        self.command_callback: Optional[Callable] = None

    def _init_tts(self):
        """Inicializar motor de text-to-speech"""
        try:
            self.tts_engine = pyttsx3.init()

            # Configurar voz en español si está disponible
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'spanish' in voice.name.lower() or 'es' in voice.id.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break

            # Configurar velocidad
            self.tts_engine.setProperty('rate', 150)

        except Exception as e:
            logger.error(f"Error inicializando TTS: {e}")
            self.tts_enabled = False

    def speak(self, text: str):
        """
        Hablar texto usando TTS

        Args:
            text: Texto a hablar
        """
        if not self.tts_enabled or not self.tts_engine:
            logger.warning("TTS no está disponible")
            return

        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"Error en TTS: {e}")

    def speak_async(self, text: str):
        """
        Hablar texto de forma asíncrona

        Args:
            text: Texto a hablar
        """
        thread = threading.Thread(target=self.speak, args=(text,))
        thread.daemon = True
        thread.start()

    def listen(self, timeout: int = 5) -> Optional[str]:
        """
        Escuchar comando de voz

        Args:
            timeout: Tiempo máximo de espera en segundos

        Returns:
            Texto reconocizado o None si no se reconoció
        """
        with sr.Microphone() as source:
            logger.info("Escuchando...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)

            try:
                audio = self.recognizer.listen(source, timeout=timeout)
            except sr.WaitTimeoutError:
                logger.info("Tiempo de espera agotado")
                return None

        try:
            if self.stt_engine == "google":
                text = self.recognizer.recognize_google(audio, language=self.language)
            elif self.stt_engine == "sphinx":
                text = self.recognizer.recognize_sphinx(audio)
            else:
                # Default a Google
                text = self.recognizer.recognize_google(audio, language=self.language)

            logger.info(f"Reconocido: {text}")
            return text

        except sr.UnknownValueError:
            logger.info("No se pudo entender el audio")
            return None
        except sr.RequestError as e:
            logger.error(f"Error en el servicio de reconocimiento: {e}")
            return None

    def listen_continuous(self, callback: Callable[[str], None]):
        """
        Escuchar continuamente en segundo plano

        Args:
            callback: Función a llamar con el texto reconocido
        """
        self.command_callback = callback
        self.is_listening = True

        def listen_thread():
            while self.is_listening:
                text = self.listen()
                if text and self.command_callback:
                    self.command_callback(text)

        thread = threading.Thread(target=listen_thread)
        thread.daemon = True
        thread.start()

    def stop_listening(self):
        """Detener escucha continua"""
        self.is_listening = False

    def process_voice_command(
        self,
        text: str,
        keywords: Dict[str, Callable] = None
    ) -> Dict[str, Any]:
        """
        Procesar comando de voz

        Args:
            text: Texto reconocido
            keywords: Diccionario de palabras clave y sus callbacks

        Returns:
            Resultado del procesamiento
        """
        text_lower = text.lower().strip()

        result = {
            "original": text,
            "processed": False,
            "action": None,
            "params": {}
        }

        # Keywords por defecto
        default_keywords = {
            "encender": lambda: {"action": "turn_on"},
            "apagar": lambda: {"action": "turn_off"},
            "activar": lambda: {"action": "turn_on"},
            "desactivar": lambda: {"action": "turn_off"},
            "estado": lambda: {"action": "get_state"},
            "temperatura": lambda: {"action": "climate", "domain": "climate"},
            "luz": lambda: {"action": "light", "domain": "light"},
            "interruptor": lambda: {"action": "switch", "domain": "switch"},
        }

        keywords = keywords or {}
        keywords.update(default_keywords)

        # Buscar keywords
        for keyword, action_func in keywords.items():
            if keyword in text_lower:
                action_info = action_func()
                result["action"] = action_info.get("action")
                result["params"] = action_info.get("params", {})
                result["processed"] = True
                break

        return result


class VoiceCommandProcessor:
    """
    Procesador de comandos de voz específico para Home Assistant
    """

    def __init__(self, ha_client, language: str = "es"):
        self.ha_client = ha_client
        self.language = language

        # Patrones de comandos
        self.command_patterns = {
            "turn_on": [
                "enciende", "encender", "activa", "activar",
                "pon", "prende", "prender"
            ],
            "turn_off": [
                "apaga", "apagar", "desactiva", "desactivar",
                "quita", "apaga", "apagar"
            ],
            "get_state": [
                "cuál es el estado", "qué estado tiene",
                "dime el estado", "estado de"
            ],
            "set_value": [
                "ajusta", "configura", "pon al", "establece"
            ],
            "toggle": [
                "alterna", "cambia", "toggle"
            ]
        }

        # Patrones de entidades
        self.entity_patterns = {
            "luz": "light",
            "lampara": "light",
            "lámpara": "light",
            "interruptor": "switch",
            "enchufe": "switch",
            "termostato": "climate",
            "aire": "climate",
            "calefacción": "climate",
            "sensor": "sensor",
            "cámara": "camera",
            "música": "media_player",
            "tv": "media_player",
            "televisión": "media_player"
        }

        # Patrones de áreas
        self.area_patterns = {
            "salón": "salon",
            "salon": "salon",
            "cocina": "cocina",
            "dormitorio": "dormitorio",
            "habitación": "dormitorio",
            "baño": "bano",
            "baño": "bano",
            "garaje": "garaje",
            "jardín": "jardin",
            "jardin": "jardin"
        }

    async def parse_command(self, text: str) -> Dict[str, Any]:
        """
        Parsear comando de voz

        Args:
            text: Texto del comando

        Returns:
            Diccionario con acción, entidad y parámetros
        """
        text_lower = text.lower().strip()

        result = {
            "action": None,
            "domain": None,
            "entity_id": None,
            "area": None,
            "value": None,
            "confidence": 0
        }

        # Detectar acción
        for action, patterns in self.command_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    result["action"] = action
                    result["confidence"] += 0.3
                    break

        # Detectar dominio/tipo de entidad
        for pattern, domain in self.entity_patterns.items():
            if pattern in text_lower:
                result["domain"] = domain
                result["confidence"] += 0.2
                break

        # Detectar área
        for pattern, area in self.area_patterns.items():
            if pattern in text_lower:
                result["area"] = area
                result["confidence"] += 0.2
                break

        # Detectar valor numérico
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            result["value"] = int(numbers[0])
            result["confidence"] += 0.1

        # Buscar entidad si tenemos dominio y área
        if result["domain"] and result["area"]:
            entities = await self.ha_client.get_entities(
                domain=result["domain"]
            )
            for entity in entities:
                attrs = entity.get("attributes", {})
                if attrs.get("area_id") == result["area"]:
                    result["entity_id"] = entity.get("entity_id")
                    result["confidence"] += 0.2
                    break

        return result