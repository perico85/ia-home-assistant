#!/bin/bash
# IA Home Assistant Add-on - Startup Script

set -e

echo "=== Iniciando IA Home Assistant ==="
echo "Version: 1.0.0"
echo ""

# Configurar variables de entorno desde opciones
export HA_URL="${HA_URL:-${SUPERVISOR_URL:-http://homeassistant:8123}}"
export HA_TOKEN="${HA_TOKEN:-}"
export OLLAMA_API_KEY="${OLLAMA_API_KEY:-}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-https://api.ollama.ai}"
export LANGUAGE="${LANGUAGE:-es}"
export SECURITY_MODE="${SECURITY_MODE:-hybrid}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Mostrar configuración
echo "Configuración:"
echo "  HA URL: ${HA_URL}"
echo "  Modelo Ollama: ${OLLAMA_MODEL}"
echo "  Idioma: ${LANGUAGE}"
echo "  Modo seguridad: ${SECURITY_MODE}"
echo ""

# Verificar que HA_TOKEN está configurado
if [ -z "$HA_TOKEN" ]; then
    echo "⚠️  ADVERTENCIA: HA_TOKEN no está configurado"
    echo "   Configure el token en las opciones del add-on"
fi

# Iniciar la aplicación
echo "Iniciando servidor..."
cd /app
exec python -m app.main