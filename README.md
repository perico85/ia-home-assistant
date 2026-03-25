# IA Home Assistant - Add-on

Asistente de inteligencia artificial con control total de Home Assistant usando modelos de Ollama Cloud o locales.

## Características

- 🤖 **Control por voz y texto** integrado con Home Assistant Assist
- 🏠 **Control total de dispositivos** - luces, interruptores, clima, etc.
- ☁️ **Ollama Cloud** - Modelos potentes sin hardware local
- 🔒 **Modos de seguridad** - safe, hybrid, unrestricted
- 🌐 **Interfaz web** con Ingress integrado
- 🇪🇸 **Multiidioma** - Español, inglés, alemán, francés, italiano, portugués

## Instalación

### Paso 1: Añadir repositorio

1. En Home Assistant, ve a **Configuración → Add-ons → Tienda de Add-ons**
2. Click en los **3 puntos** (esquina superior derecha) → **Repositorios**
3. Añade la URL: `https://github.com/perico85/ia-home-assistant`
4. Click en **Añadir**
5. Busca **"IA Home Assistant"** en la tienda
6. Click en **Instalar**

### Paso 2: Configurar el Add-on

#### Ollama Cloud (recomendado)

1. Obtén tu API key en [ollama.com/settings/keys](https://ollama.com/settings/keys)
2. Crea un token de larga duración en Home Assistant:
   - Ve a tu perfil (abajo a la izquierda)
   - Baja a **Tokens de acceso de larga duración**
   - Crea un nuevo token
3. Configura el add-on:

| Campo | Valor |
|-------|-------|
| `ha_url` | `http://homeassistant:8123` |
| `ha_token` | Tu token de larga duración |
| `ollama_mode` | `cloud` |
| `ollama_api_key` | Tu API key de Ollama Cloud |
| `ollama_model` | `minimax-m2.7:cloud` (o el modelo que prefieras) |
| `ollama_base_url` | **Déjalo vacío** - se usa automáticamente `https://ollama.com` |
| `language` | `es` |
| `security_mode` | `hybrid` |

> **Nota**: La URL de Ollama Cloud (`https://ollama.com`) se configura automáticamente cuando seleccionas el modo `cloud`. No necesitas introducirla manualmente.

#### Ollama Local

Si tienes Ollama instalado localmente:

| Field | Value |
|-------|-------|
| `ollama_mode` | `local` |
| `ollama_base_url` | `http://localhost:11434` (o la URL de tu servidor Ollama) |
| `ollama_model` | `llama3.2` (o el modelo que tengas instalado) |

### Paso 3: Integrar con Assist (opcional)

Para usar con el asistente de voz de Home Assistant:

1. **Reinicia Home Assistant** después de instalar el add-on
2. Ve a **Configuración → Dispositivos y Servicios**
3. Click en **Añadir integración**
4. Busca **"IA Home Assistant"**
5. Configura la URL del add-on: `http://homeassistant:8080`
6. Ve a **Configuración → Asistentes de voz**
7. Crea o edita un asistente
8. En **Agente de conversación**, selecciona **"IA Assistant"**

## Modelos Cloud Disponibles

| Modelo | Descripción | Uso recomendado |
|--------|-------------|-----------------|
| `minimax-m2.7:cloud` | MiniMax M2.7 | Mejor rendimiento general |
| `llama3.2:cloud` | Llama 3.2 | Conversación natural |
| `llama3.1:70b-cloud` | Llama 3.1 70B | Tareas complejas |
| `gpt-oss:120b-cloud` | OpenAI-compatible | Compatible con herramientas |

## Uso

### Interfaz Web (Ingress)

1. Click en **"IA Assistant"** en el sidebar de Home Assistant
2. O ve a **Configuración → Add-ons → IA Home Assistant → Abrir interfaz web**

### API REST

```bash
# Chat
curl -X POST http://homeassistant:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Enciende la luz del salón"}'

# Obtener entidades
curl http://homeassistant:8080/api/entities

# Cambiar modelo
curl -X PUT http://homeassistant:8080/api/model \
  -H "Content-Type: application/json" \
  -d '{"model": "minimax-m2.7:cloud"}'
```

## Solución de problemas

### El add-on no inicia

1. Verifica que el token de Home Assistant es correcto
2. Verifica que la API key de Ollama Cloud es válida
3. Revisa los logs: `ha addons logs ia_home_assistant`

### No se puede conectar a Home Assistant

- El `ha_url` debe ser `http://homeassistant:8123` (no tu URL externa)
- El token debe ser de un usuario administrador

### No se puede conectar a Ollama Cloud

- Verifica que el modo está en `cloud`
- Verifica que la API key es válida
- La URL correcta es `https://ollama.com` (se configura automáticamente)

### La integración con Assist no aparece

1. Reinicia Home Assistant
2. Verifica que el add-on está ejecutándose
3. Comprueba que el custom_component se instaló en `/config/custom_components/ia_assistant`

## Soporte

- Documentación: [GitHub](https://github.com/perico85/ia-home-assistant)
- Issues: [GitHub Issues](https://github.com/perico85/ia-home-assistant/issues)

## Licencia

MIT License