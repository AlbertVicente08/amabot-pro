# 1. Usamos la imagen OFICIAL de Playwright (Hecha por Microsoft)
# Esta imagen ya trae Python, Chromium, Firefox y todas las dependencias de sistema.
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# 2. Preparamos la carpeta
WORKDIR /app

# 3. Copiamos tus archivos
COPY . .

# 4. Instalamos las librerías de tu bot (aiogram, etc.)
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# 5. Por seguridad, ejecutamos la instalación de drivers una vez más
# (Aunque la imagen ya los trae, esto asegura que estén linkeados)
RUN playwright install chromium

# 6. Arrancamos el bot
CMD ["python", "main.py"]