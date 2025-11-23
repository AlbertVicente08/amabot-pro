import asyncio
from aiogram import Bot

# TUS DATOS
TOKEN = "8570507078:AAHXOnOxZW5RG1TQFwbl76omrMkQTJlENW4"
CHANNEL = "@ChollosVipAmazon" # Asegúrate de que está escrito EXACTO

async def test_connection():
    print(f"📡 Intentando conectar con {CHANNEL}...")
    bot = Bot(token=TOKEN)
    
    try:
        # Intentamos enviar un mensaje simple
        await bot.send_message(chat_id=CHANNEL, text="🔔 **¡TEST DE CONEXIÓN EXITOSO!**\nSi lees esto, el bot es Admin.", parse_mode="Markdown")
        print("\n✅ ¡ÉXITO! El mensaje se envió. El problema NO es el canal.")
        print("El fallo debe estar en la base de datos (el bot no detecta la bajada de precio).")
        
    except Exception as e:
        print("\n❌ ¡ERROR CRÍTICO! Telegram rechazó el mensaje.")
        print(f"Detalle del error: {e}")
        print("\nSOLUCIÓN:")
        print("1. Ve al canal > Admins > Asegúrate que 'Amabot' está ahí.")
        print("2. Asegúrate que tiene el permiso 'Publicar Mensajes' activado.")
        print("3. Escribe un mensaje tú en el canal para asegurarte que no está en modo lectura.")

    await bot.session.close()

if __name__ == "__main__":
    asyncio.run(test_connection())