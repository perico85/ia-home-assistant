/**
 * Grabador de voz para IA Home Assistant
 * Maneja la captura y procesamiento de comandos de voz
 */

class VoiceRecorder {
    constructor(options = {}) {
        this.options = {
            language: options.language || 'es-ES',
            continuous: options.continuous || false,
            onResult: options.onResult || (() => {}),
            onError: options.onError || (() => {}),
            onstart: options.onStart || (() => {}),
            onEnd: options.onEnd || (() => {})
        };

        this.recognition = null;
        this.isRecording = false;
        this.isSupported = false;

        this.init();
    }

    /**
     * Inicializar reconocimiento de voz
     */
    init() {
        // Verificar soporte
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            console.warn('Reconocimiento de voz no soportado');
            this.isSupported = false;
            return;
        }

        this.isSupported = true;
        this.recognition = new SpeechRecognition();

        // Configuración
        this.recognition.lang = this.options.language;
        this.recognition.continuous = this.options.continuous;
        this.recognition.interimResults = false;
        this.recognition.maxAlternatives = 1;

        // Eventos
        this.recognition.onstart = () => {
            this.isRecording = true;
            this.options.onStart();
        };

        this.recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            const confidence = event.results[0][0].confidence;
            this.options.onResult(transcript, confidence);
        };

        this.recognition.onerror = (event) => {
            this.isRecording = false;
            this.options.onError(event.error);
        };

        this.recognition.onend = () => {
            this.isRecording = false;
            this.options.onEnd();
        };
    }

    /**
     * Iniciar grabación
     */
    start() {
        if (!this.isSupported) {
            this.options.onError('not_supported');
            return;
        }

        if (this.isRecording) {
            return;
        }

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Error iniciando reconocimiento:', error);
        }
    }

    /**
     * Detener grabación
     */
    stop() {
        if (!this.isSupported || !this.isRecording) {
            return;
        }

        try {
            this.recognition.stop();
        } catch (error) {
            console.error('Error deteniendo reconocimiento:', error);
        }
    }

    /**
     * Alternar grabación
     */
    toggle() {
        if (this.isRecording) {
            this.stop();
        } else {
            this.start();
        }
    }

    /**
     * Cambiar idioma
     */
    setLanguage(lang) {
        this.options.language = lang;
        if (this.recognition) {
            this.recognition.lang = lang;
        }
    }
}

/**
 * Sintetizador de voz (Text-to-Speech)
 */
class VoiceSynthesizer {
    constructor(options = {}) {
        this.options = {
            language: options.language || 'es-ES',
            rate: options.rate || 1.0,
            pitch: options.pitch || 1.0,
            volume: options.volume || 1.0
        };

        this.isSupported = 'speechSynthesis' in window;
        this.voices = [];
        this.currentVoice = null;

        if (this.isSupported) {
            this.init();
        }
    }

    /**
     * Inicializar sintetizador
     */
    init() {
        // Cargar voces
        const loadVoices = () => {
            this.voices = speechSynthesis.getVoices();
            this.selectVoice();
        };

        // Cargar voces (algunos navegadores necesitan esperar)
        if (speechSynthesis.onvoiceschanged !== undefined) {
            speechSynthesis.onvoiceschanged = loadVoices;
        } else {
            loadVoices();
        }
    }

    /**
     * Seleccionar voz preferida
     */
    selectVoice() {
        // Buscar voz en español
        for (const voice of this.voices) {
            if (voice.lang.startsWith('es')) {
                this.currentVoice = voice;
                break;
            }
        }

        // Si no hay voz en español, usar la primera disponible
        if (!this.currentVoice && this.voices.length > 0) {
            this.currentVoice = this.voices[0];
        }
    }

    /**
     * Hablar texto
     */
    speak(text, options = {}) {
        if (!this.isSupported) {
            console.warn('Síntesis de voz no soportada');
            return Promise.reject('not_supported');
        }

        return new Promise((resolve, reject) => {
            const utterance = new SpeechSynthesisUtterance(text);

            // Configurar
            utterance.lang = options.language || this.options.language;
            utterance.rate = options.rate || this.options.rate;
            utterance.pitch = options.pitch || this.options.pitch;
            utterance.volume = options.volume || this.options.volume;

            if (this.currentVoice) {
                utterance.voice = this.currentVoice;
            }

            // Eventos
            utterance.onend = () => resolve();
            utterance.onerror = (event) => reject(event.error);

            // Hablar
            speechSynthesis.speak(utterance);
        });
    }

    /**
     * Detener síntesis
     */
    stop() {
        if (this.isSupported) {
            speechSynthesis.cancel();
        }
    }

    /**
     * Pausar síntesis
     */
    pause() {
        if (this.isSupported) {
            speechSynthesis.pause();
        }
    }

    /**
     * Reanudar síntesis
     */
    resume() {
        if (this.isSupported) {
            speechSynthesis.resume();
        }
    }

    /**
     * Verificar si está hablando
     */
    isSpeaking() {
        return this.isSupported && speechSynthesis.speaking;
    }
}

/**
 * Manejador de comandos de voz
 */
class VoiceCommandHandler {
    constructor(options = {}) {
        this.recorder = new VoiceRecorder({
            language: options.language || 'es-ES',
            onResult: (text, confidence) => this.handleResult(text, confidence),
            onError: (error) => this.handleError(error)
        });

        this.synthesizer = new VoiceSynthesizer({
            language: options.language || 'es-ES'
        });

        this.commands = new Map();
        this.onCommand = options.onCommand || (() => {});

        // Comandos por defecto
        this.registerDefaultCommands();
    }

    /**
     * Registrar comandos por defecto
     */
    registerDefaultCommands() {
        // Encender
        this.registerCommand(/enciende|encender|activa|activar|prende|prender/i, 'turn_on');

        // Apagar
        this.registerCommand(/apaga|apagar|desactiva|desactivar|quita/i, 'turn_off');

        // Alternar
        this.registerCommand(/alterna|cambia|toggle/i, 'toggle');

        // Estado
        this.registerCommand(/estado|cómo está|qué estado|dime el estado/i, 'get_state');

        // Temperatura
        this.registerCommand(/temperatura|cuánto calor|cuánto frío/i, 'temperature');

        // Luces
        this.registerCommand(/luz|luces|lámpara|lámparas/i, 'light');

        // Interruptor
        this.registerCommand(/interruptor|enchufe|enchufes/i, 'switch');

        // Todas
        this.registerCommand(/todas|todos|todas las|todos los/i, 'all');
    }

    /**
     * Registrar nuevo comando
     */
    registerCommand(pattern, action) {
        this.commands.set(pattern, action);
    }

    /**
     * Manejar resultado del reconocimiento
     */
    handleResult(text, confidence) {
        console.log('Reconocido:', text, 'Confianza:', confidence);

        // Parsear comando
        const command = this.parseCommand(text);

        if (command) {
            this.onCommand(command);
        } else {
            // No se reconoció como comando específico, enviar como texto
            this.onCommand({
                type: 'text',
                text: text,
                confidence: confidence
            });
        }
    }

    /**
     * Parsear comando de voz
     */
    parseCommand(text) {
        const result = {
            text: text,
            action: null,
            entity: null,
            area: null,
            value: null
        };

        // Buscar acción
        for (const [pattern, action] of this.commands) {
            if (pattern.test(text)) {
                result.action = action;
                break;
            }
        }

        // Buscar entidad
        const entityPatterns = {
            luz: 'light',
            luces: 'light',
            lámpara: 'light',
            interruptor: 'switch',
            termostato: 'climate',
            aire: 'climate',
            sensor: 'sensor'
        };

        for (const [pattern, domain] of Object.entries(entityPatterns)) {
            if (text.toLowerCase().includes(pattern)) {
                result.entity = domain;
                break;
            }
        }

        // Buscar área
        const areaPatterns = {
            salón: 'salon',
            salon: 'salon',
            cocina: 'cocina',
            dormitorio: 'dormitorio',
            habitación: 'dormitorio',
            baño: 'bano',
            garaje: 'garaje',
            jardín: 'jardin'
        };

        for (const [pattern, area] of Object.entries(areaPatterns)) {
            if (text.toLowerCase().includes(pattern)) {
                result.area = area;
                break;
            }
        }

        // Buscar valor numérico
        const numberMatch = text.match(/(\d+)/);
        if (numberMatch) {
            result.value = parseInt(numberMatch[1]);
        }

        return result.action || result.entity ? result : null;
    }

    /**
     * Manejar error
     */
    handleError(error) {
        console.error('Error de reconocimiento:', error);
        this.onCommand({
            type: 'error',
            error: error
        });
    }

    /**
     * Iniciar escucha
     */
    startListening() {
        this.recorder.start();
    }

    /**
     * Detener escucha
     */
    stopListening() {
        this.recorder.stop();
    }

    /**
     * Hablar respuesta
     */
    speak(text) {
        return this.synthesizer.speak(text);
    }
}

// Exportar clases
window.VoiceRecorder = VoiceRecorder;
window.VoiceSynthesizer = VoiceSynthesizer;
window.VoiceCommandHandler = VoiceCommandHandler;