# 1. Usamos una base limpia de Python
FROM python:3.10-slim

# 2. Definimos dónde se guardarán los navegadores para que no se pierdan
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers

# 3. Instalamos las herramientas básicas de Linux
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# 4. Preparamos la carpeta
WORKDIR /app

# 5. Copiamos los archivos
COPY . .

# 6. Instalamos las librerías de Python (incluyendo Playwright 1.44.0)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 7. ¡PASO CRÍTICO! Instalamos el navegador y las dependencias del sistema
# Usamos 'python -m' para asegurar que usamos el playwright correcto
RUN python -m playwright install --with-deps chromium

# 8. Arrancamos el bot
CMD ["python", "main.py"]