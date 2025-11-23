# Usamos la imagen oficial de Playwright con Python 3.10 (Estable y compatible)
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Preparamos la carpeta
WORKDIR /app

# Copiamos tus archivos
COPY . .

# Instalamos las librerías
# (Al ser Python 3.10, descargará los 'wheels' ya hechos y no fallará compilando)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Re-instalamos dependencias de navegador por seguridad
RUN playwright install chromium
RUN playwright install-deps

# Arrancamos
CMD ["python", "main.py"]