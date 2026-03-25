#!/bin/bash
# Instalar el custom_component en Home Assistant

echo "=== Instalando integración IA Assistant ==="

# Directorio de destino en Home Assistant
HA_CUSTOM_COMPONENTS="/config/custom_components"
IA_ASSISTANT_DIR="${HA_CUSTOM_COMPONENTS}/ia_assistant"

# Crear directorio si no existe
mkdir -p "${HA_CUSTOM_COMPONENTS}"

# Copiar custom_component
echo "Copiando custom_component a ${IA_ASSISTANT_DIR}..."

# Verificar si ya existe y hacer backup
if [ -d "${IA_ASSISTANT_DIR}" ]; then
    echo "Backup de versión anterior..."
    mv "${IA_ASSISTANT_DIR}" "${IA_ASSISTANT_DIR}.backup.$(date +%s)"
fi

# Copiar desde el addon
cp -r /app/custom_components/ia_assistant "${HA_CUSTOM_COMPONENTS}/"

# Verificar que se copió correctamente
if [ -d "${IA_ASSISTANT_DIR}" ]; then
    echo "✅ Integración instalada correctamente en ${IA_ASSISTANT_DIR}"
    echo ""
    echo "Para activar la integración:"
    echo "1. Ve a Configuración > Dispositivos y Servicios"
    echo "2. Haz clic en 'Añadir integración'"
    echo "3. Busca 'IA Home Assistant'"
    echo "4. Sigue los pasos de configuración"
    echo ""
else
    echo "❌ Error instalando la integración"
fi

echo "=== Instalación completada ==="