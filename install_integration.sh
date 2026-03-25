#!/bin/bash
# Instalar el custom_component en Home Assistant
# Este script se ejecuta de forma segura sin bloquear el sistema

echo "=== Instalando integración IA Assistant ==="

# Directorio de destino en Home Assistant
HA_CUSTOM_COMPONENTS="/config/custom_components"
IA_ASSISTANT_DIR="${HA_CUSTOM_COMPONENTS}/ia_assistant"

# Función para instalar de forma segura
install_integration() {
    # Verificar que el directorio /config existe
    if [ ! -d "/config" ]; then
        echo "⚠️  Directorio /config no disponible, omitiendo instalación de integración"
        echo "   La integración se puede instalar manualmente desde HACS"
        return 0
    fi

    # Crear directorio custom_components si no existe
    if ! mkdir -p "${HA_CUSTOM_COMPONENTS}" 2>/dev/null; then
        echo "⚠️  No se puede crear directorio ${HA_CUSTOM_COMPONENTS}"
        echo "   La integración se puede instalar manualmente desde HACS"
        return 0
    fi

    # Verificar que tenemos permisos de escritura
    if [ ! -w "${HA_CUSTOM_COMPONENTS}" ]; then
        echo "⚠️  Sin permisos de escritura en ${HA_CUSTOM_COMPONENTS}"
        echo "   La integración se puede instalar manualmente desde HACS"
        return 0
    fi

    # Verificar si ya existe y hacer backup
    if [ -d "${IA_ASSISTANT_DIR}" ]; then
        echo "Actualizando integración existente..."
        rm -rf "${IA_ASSISTANT_DIR}.old" 2>/dev/null
        mv "${IA_ASSISTANT_DIR}" "${IA_ASSISTANT_DIR}.old" 2>/dev/null || {
            echo "⚠️  No se pudo hacer backup, omitiendo instalación"
            return 0
        }
    fi

    # Copiar desde el addon (con timeout para evitar bloqueos)
    echo "Copiando archivos..."
    if timeout 30 cp -r /app/custom_components/ia_assistant "${HA_CUSTOM_COMPONENTS}/" 2>/dev/null; then
        if [ -d "${IA_ASSISTANT_DIR}" ]; then
            echo "✅ Integración instalada correctamente"
            echo ""
            echo "Para activar la integración:"
            echo "1. Reinicia Home Assistant"
            echo "2. Ve a Configuración > Dispositivos y Servicios"
            echo "3. Añadir integración > Buscar 'IA Home Assistant'"
            echo ""
            # Limpiar backup antiguo
            rm -rf "${IA_ASSISTANT_DIR}.old" 2>/dev/null
            return 0
        fi
    fi

    # Restaurar backup si falló la instalación
    if [ -d "${IA_ASSISTANT_DIR}.old" ]; then
        mv "${IA_ASSISTANT_DIR}.old" "${IA_ASSISTANT_DIR}" 2>/dev/null
    fi

    echo "❌ Error instalando la integración"
    echo "   Se puede instalar manualmente copiando la carpeta custom_components/ia_assistant"
    return 1
}

# Ejecutar instalación con timeout
install_integration

echo "=== Continuando con el inicio del addon ==="