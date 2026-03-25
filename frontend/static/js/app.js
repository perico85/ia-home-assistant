/**
 * IA Home Assistant - JavaScript Principal
 */

// Configuración
const CONFIG = {
    wsUrl: `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`,
    reconnectDelay: 3000,
    maxReconnectAttempts: 5
};

// Estado de la aplicación
const state = {
    socket: null,
    connected: false,
    reconnectAttempts: 0,
    isTyping: false,
    isRecording: false,
    currentModel: 'llama3.2',
    messages: [],
    entities: []
};

// Elementos del DOM
const elements = {
    chatMessages: document.getElementById('chat-messages'),
    chatInput: document.getElementById('chat-input'),
    sendButton: document.getElementById('send-button'),
    voiceButton: document.getElementById('voice-button'),
    modelSelect: document.getElementById('model-select'),
    statusIndicator: document.getElementById('status-indicator'),
    statusText: document.getElementById('status-text'),
    quickActions: document.querySelectorAll('.quick-action'),
    modal: document.getElementById('confirmation-modal'),
    modalTitle: document.getElementById('modal-title'),
    modalMessage: document.getElementById('modal-message'),
    modalConfirm: document.getElementById('modal-confirm'),
    modalCancel: document.getElementById('modal-cancel')
};

/**
 * Conectar WebSocket
 */
function connectWebSocket() {
    updateStatus('connecting', 'Conectando...');

    state.socket = io(CONFIG.wsUrl, {
        transports: ['websocket'],
        reconnection: true,
        reconnectionDelay: CONFIG.reconnectDelay,
        reconnectionAttempts: CONFIG.maxReconnectAttempts
    });

    // Eventos del socket
    state.socket.on('connect', () => {
        console.log('Conectado al servidor');
        state.connected = true;
        state.reconnectAttempts = 0;
        updateStatus('connected', 'Conectado');
    });

    state.socket.on('disconnect', () => {
        console.log('Desconectado del servidor');
        state.connected = false;
        updateStatus('disconnected', 'Desconectado');
    });

    state.socket.on('error', (error) => {
        console.error('Error de conexión:', error);
        updateStatus('disconnected', 'Error de conexión');
    });

    state.socket.on('connected', (data) => {
        console.log('Servidor listo:', data);
    });

    state.socket.on('stream', (data) => {
        handleStream(data);
    });

    state.socket.on('response', (data) => {
        handleResponse(data);
    });

    state.socket.on('thinking', (data) => {
        showTypingIndicator();
    });

    state.socket.on('action_executed', (data) => {
        handleActionExecuted(data);
    });

    state.socket.on('action_requires_confirmation', (data) => {
        showConfirmationModal(data);
    });

    state.socket.on('error', (data) => {
        showError(data.message);
    });

    state.socket.on('entities', (data) => {
        state.entities = data.entities;
        updateEntitiesList(data.entities);
    });

    state.socket.on('model_changed', (data) => {
        state.currentModel = data.model;
        showNotification(`Modelo cambiado a: ${data.model}`);
    });
}

/**
 * Actualizar indicador de estado
 */
function updateStatus(status, text) {
    const dot = elements.statusIndicator?.querySelector('.status-dot');
    const statusText = elements.statusText;

    if (dot) {
        dot.className = 'status-dot';
        if (status === 'disconnected') {
            dot.classList.add('disconnected');
        } else if (status === 'connecting') {
            dot.classList.add('connecting');
        }
    }

    if (statusText) {
        statusText.textContent = text;
    }
}

/**
 * Enviar mensaje
 */
function sendMessage() {
    const input = elements.chatInput;
    const message = input.value.trim();

    if (!message || !state.connected) return;

    // Limpiar input
    input.value = '';
    autoResize();

    // Añadir mensaje del usuario
    addMessage('user', message);

    // Enviar al servidor
    state.socket.emit('message', { message });

    // Mostrar indicador de escritura
    showTypingIndicator();
}

/**
 * Añadir mensaje al chat
 */
function addMessage(role, content, isThinking = false) {
    const container = elements.chatMessages;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;

    if (isThinking) {
        messageDiv.innerHTML = `
            <div class="typing-indicator">
                <span></span><span></span><span></span>
            </div>
        `;
        messageDiv.id = 'typing-indicator';
    } else {
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.textContent = content;
        messageDiv.appendChild(contentDiv);
    }

    container.appendChild(messageDiv);
    scrollToBottom();
}

/**
 * Mostrar indicador de escritura
 */
function showTypingIndicator() {
    // Remover indicador anterior si existe
    const existing = document.getElementById('typing-indicator');
    if (existing) existing.remove();

    addMessage('assistant', '', true);
    state.isTyping = true;
}

/**
 * Ocultar indicador de escritura
 */
function hideTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
    state.isTyping = false;
}

/**
 * Manejar stream de respuesta
 */
function handleStream(data) {
    hideTypingIndicator();

    // Obtener último mensaje del asistente o crear uno nuevo
    let lastMessage = elements.chatMessages.querySelector('.message-assistant:last-child .message-content');

    if (!lastMessage) {
        addMessage('assistant', data.chunk);
    } else {
        lastMessage.textContent += data.chunk;
    }

    scrollToBottom();
}

/**
 * Manejar respuesta completa
 */
function handleResponse(data) {
    hideTypingIndicator();

    if (data.success) {
        // La respuesta ya se mostró via stream
        state.messages.push({
            role: 'assistant',
            content: data.message
        });
    } else {
        showError(data.error || 'Error al procesar la solicitud');
    }
}

/**
 * Manejar acción ejecutada
 */
function handleActionExecuted(data) {
    if (data.success) {
        showNotification('Acción ejecutada correctamente');
    } else {
        showError(`Error en la acción: ${data.error || 'Desconocido'}`);
    }
}

/**
 * Mostrar error
 */
function showError(message) {
    hideTypingIndicator();
    addMessage('error', message);
}

/**
 * Mostrar notificación
 */
function showNotification(message) {
    // Crear notificación temporal
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--success-color);
        color: white;
        padding: 12px 24px;
        border-radius: 8px;
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

/**
 * Mostrar modal de confirmación
 */
function showConfirmationModal(data) {
    hideTypingIndicator();

    elements.modalTitle.textContent = 'Confirmar acción';
    elements.modalMessage.textContent = data.message || '¿Estás seguro de que quieres realizar esta acción?';
    elements.modal.dataset.action = JSON.stringify(data.action);
    elements.modal.classList.add('show');
}

/**
 * Confirmar acción
 */
function confirmAction() {
    const action = JSON.parse(elements.modal.dataset.action || '{}');
    state.socket.emit('confirm_action', { action });
    closeModal();
}

/**
 * Cerrar modal
 */
function closeModal() {
    elements.modal.classList.remove('show');
}

/**
 * Actualizar lista de entidades
 */
function updateEntitiesList(entities) {
    const list = document.getElementById('entities-list');
    if (!list) return;

    list.innerHTML = entities.slice(0, 5).map(entity => {
        const name = entity.attributes?.friendly_name || entity.entity_id;
        const state = entity.state;
        return `
            <li class="entity-item" data-entity-id="${entity.entity_id}">
                <span class="entity-name">${name}</span>
                <span class="entity-state">${state}</span>
            </li>
        `;
    }).join('');
}

/**
 * Scroll al fondo del chat
 */
function scrollToBottom() {
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

/**
 * Auto-resize del textarea
 */
function autoResize() {
    const input = elements.chatInput;
    input.style.height = 'auto';
    input.style.height = Math.min(input.scrollHeight, 120) + 'px';
}

/**
 * Iniciar grabación de voz
 */
function startVoiceRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        showError('Reconocimiento de voz no soportado en este navegador');
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();

    recognition.lang = 'es-ES';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
        elements.voiceButton.classList.add('recording');
        state.isRecording = true;
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        elements.chatInput.value = transcript;
        autoResize();
    };

    recognition.onerror = (event) => {
        console.error('Error de reconocimiento:', event.error);
        elements.voiceButton.classList.remove('recording');
        state.isRecording = false;
    };

    recognition.onend = () => {
        elements.voiceButton.classList.remove('recording');
        state.isRecording = false;
    };

    recognition.start();
}

/**
 * Cambiar modelo
 */
function changeModel() {
    const model = elements.modelSelect?.value;
    if (model && state.connected) {
        state.socket.emit('change_model', { model });
    }
}

/**
 * Manejar acción rápida
 */
function handleQuickAction(action) {
    const commands = {
        'lights-on': 'Enciende todas las luces',
        'lights-off': 'Apaga todas las luces',
        'status': '¿Cuál es el estado del sistema?',
        'temperature': '¿Cuál es la temperatura actual?'
    };

    const command = commands[action];
    if (command) {
        elements.chatInput.value = command;
        sendMessage();
    }
}

/**
 * Configurar eventos
 */
function setupEventListeners() {
    // Enviar mensaje con Enter
    elements.chatInput?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Botón de enviar
    elements.sendButton?.addEventListener('click', sendMessage);

    // Botón de voz
    elements.voiceButton?.addEventListener('click', startVoiceRecording);

    // Selector de modelo
    elements.modelSelect?.addEventListener('change', changeModel);

    // Acciones rápidas
    elements.quickActions?.forEach(btn => {
        btn.addEventListener('click', () => {
            handleQuickAction(btn.dataset.action);
        });
    });

    // Modal de confirmación
    elements.modalConfirm?.addEventListener('click', confirmAction);
    elements.modalCancel?.addEventListener('click', closeModal);

    // Auto-resize
    elements.chatInput?.addEventListener('input', autoResize);
}

/**
 * Inicializar aplicación
 */
function init() {
    console.log('Inicializando IA Home Assistant...');

    // Configurar eventos
    setupEventListeners();

    // Conectar WebSocket
    connectWebSocket();

    // Mensaje inicial
    setTimeout(() => {
        addMessage('assistant', '¡Hola! Soy tu asistente de Home Assistant. ¿En qué puedo ayudarte?');
    }, 500);
}

// Iniciar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', init);