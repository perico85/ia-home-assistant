# IA Home Assistant Add-on
# Asistente IA con control total de Home Assistant usando Ollama Cloud

FROM python:3.11-slim

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar requirements primero para cachear dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app/ ./app/
COPY frontend/ ./frontend/

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main
ENV FLASK_ENV=production

# Puerto de la aplicación
EXPOSE 8080

# Comando de inicio
CMD ["python", "-m", "app.main"]