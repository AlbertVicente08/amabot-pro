FROM python:3.10-slim

# 1. Instalar herramientas del sistema
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. Preparar carpeta
WORKDIR /app

# 3. Copiar tus archivos
COPY . .

# 4. Instalar librerías de Python
RUN pip install --no-cache-dir -r requirements.txt

# 5. INSTALAR NAVEGADORES (CRÍTICO PARA TU BOT)
RUN playwright install chromium
RUN playwright install-deps

# 6. Arrancar el bot
CMD ["python", "main.py"]