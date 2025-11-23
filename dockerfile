# Usamos Python 3.10 ligero
FROM python:3.10-slim

# 1. INSTALAR HERRAMIENTAS DE SISTEMA (CRÍTICO)
# Añadimos 'build-essential' y 'python3-dev' para poder compilar las librerías que fallaban
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    build-essential \
    python3-dev \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 2. Preparar carpeta
WORKDIR /app

# 3. Copiar archivos
COPY . .

# 4. Instalar librerías de Python
# Actualizamos pip primero para evitar errores viejos
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Instalar navegador Chromium para el bot
RUN playwright install chromium

# 6. Arrancar
CMD ["python", "main.py"]