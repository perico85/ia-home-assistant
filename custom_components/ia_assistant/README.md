# IA Assistant - Custom Component para Home Assistant

Integración que permite usar modelos de Ollama Cloud como asistente de voz en Home Assistant.

## Instalación

### HACS (Recomendado)

1. Abre **HACS** en Home Assistant
2. Ve a **Integraciones**
3. Click en **+** → **Repositorios personalizados**
4. Añade: `https://github.com/tu-usuario/ia-home-assistant`
5. Categoría: **Integración**
6. Busca "IA Assistant" e instala
7. Reinicia Home Assistant

### Manual

1. Copia la carpeta `custom_components/ia_assistant` a `/config/custom_components/ia_assistant/`
2. Reinicia Home Assistant

## Configuración

1. Ve a **Configuración → Dispositivos y Servicios**
2. Click en **+ Añadir Integración**
3. Busca "IA Assistant"
4. Configura:

```yaml
llm_provider: "ollama_cloud"  # ollama_cloud, ollama_local, openai
llm_model: "minimax-m2.7:cloud"
api_key: "tu-api-key"
security_mode: "hybrid"
language: "es"
```

## Uso con Assist

1. Ve a **Configuración → Asistente de voz**
2. Selecciona **IA Assistant** como agente predeterminado
3. Usa comandos de voz o texto:
   - "Enciende las luces del salón"
   - "¿Cuál es la temperatura?"
   - "Apaga todo"

## Servicios disponibles

### `ia_assistant.chat`
Envía un mensaje al asistente.

```yaml
service: ia_assistant.chat
data:
  message: "¿Cuál es la temperatura del salón?"
```

### `ia_assistant.set_model`
Cambia el modelo de IA.

```yaml
service: ia_assistant.set_model
data:
  model: "llama3.1:70b-cloud"
```

### `ia_assistant.clear_history`
Limpia el historial de conversación.

```yaml
service: ia_assistant.clear_history
```

## Modelos soportados

Ver lista completa en: https://ollama.com/search?c=cloud

Populares:
- `minimax-m2.7:cloud`
- `llama3.2:cloud`
- `llama3.1:70b-cloud`
- `gpt-oss:120b-cloud`
- `mixtral-8x22b-cloud`