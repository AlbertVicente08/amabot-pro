# Usamos Python ligero normal
FROM python:3.10-slim

# 1. Instalar herramientas básicas del sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. Preparar carpeta de trabajo
WORKDIR /app

# 3. Copiar tus archivos al servidor
COPY . .

# 4. Instalar las librerías de tu requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 5. ¡ESTO ES LO QUE ARREGLA EL ERROR!
# Forzamos la instalación de Chromium y sus dependencias de Linux
RUN playwright install --with-deps chromium

# 6. Arrancar el bot
CMD ["python", "main.py"]