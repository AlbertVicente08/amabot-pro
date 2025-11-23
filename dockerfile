# Usamos Python oficial
FROM python:3.10-slim

# 1. Instalar dependencias del sistema necesarias para Playwright
# Esta lista es la oficial de Microsoft para que Chrome funcione en Linux
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
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
RUN pip install --no-cache-dir -r requirements.txt

# 5. INSTALAR NAVEGADORES (Aquí está la clave)
# Esto descarga el navegador exacto que pide la librería
RUN playwright install chromium

# 6. Arrancar
CMD ["python", "main.py"]