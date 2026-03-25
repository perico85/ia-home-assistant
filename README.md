# IA Home Assistant - Add-on

Asistente de inteligencia artificial con control total de Home Assistant usando modelos de Ollama Cloud o locales.

## Instalación

### Método 1: Repositorio en Home Assistant

1. En Home Assistant, ve a **Configuración → Add-ons → Tienda de Add-ons**
2. Click en los **3 puntos** → **Repositorios**
3. Añade la URL: `https://github.com/tu-usuario/ia-home-assistant`
4. Busca "IA Home Assistant" e instala

### Método 2: Instalación Local

1. Copia la carpeta `ia-home-assistant` a `/config/addons/local/`
2. Reinicia Home Assistant
3. Ve a **Configuración → Add-ons → Tienda**
4. Busca "IA Home Assistant" e instala

## Configuración

### Ollama Cloud (recomendado)

```yaml
ollama_mode: "cloud"
ollama_api_key: "tu-api-key"  # Obtener en ollama.com/settings/keys
ollama_model: "minimax-m2.7:cloud"
ha_token: "tu-long-lived-token"
language: "es"
security_mode: "hybrid"
```

### Ollama Local

```yaml
ollama_mode: "local"
ollama_model: "llama3.2"
ha_token: "tu-long-lived-token"
language: "es"
security_mode: "hybrid"
```

## Modelos Cloud Disponibles

| Modelo | Descripción |
|--------|-------------|
| `minimax-m2.7:cloud` | MiniMax M2.7 (potente) |
| `llama3.2:cloud` | Llama 3.2 en cloud |
| `llama3.1:70b-cloud` | Llama 3.1 70B |
| `gpt-oss:120b-cloud` | OpenAI-compatible |
| `mixtral-8x22b-cloud` | Mixtral 8x22B |

## Uso

### Chat Web
Abre `http://homeassistant:8080` para acceder al chat.

### API REST
```bash
# Chat
curl -X POST http://homeassistant:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Enciende la luz del salón"}'

# Cambiar modelo
curl -X PUT http://homeassistant:8080/api/model \
  -d '{"model": "llama3.1:70b-cloud"}'
```

### CLI
```bash
docker exec -it ia-home-assistant python -m app.main --cli
```

## Soporte

- Documentación: [GitHub](https://github.com/tu-usuario/ia-home-assistant)
- Issues: [GitHub Issues](https://github.com/tu-usuario/ia-home-assistant/issues)

## Licencia

MIT License