import asyncio
import sqlite3
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- TUS DATOS ---
TOKEN = "8570507078:AAHXOnOxZW5RG1TQFwbl76omrMkQTJlENW4"
# -----------------

async def enviar_alerta_falsa():
    # 1. Conectamos a la BD para coger la foto y el nombre real del producto que acabas de subir
    conn = sqlite3.connect('bot_chollos.db')
    cursor = conn.cursor()
    
    try:
        # Cogemos el último producto añadido
        cursor.execute("SELECT user_id, product_name, product_url, image_url, current_price FROM tracking ORDER BY id DESC LIMIT 1")
        producto = cursor.fetchone()
        
        if not producto:
            print("❌ No tienes productos. Añade uno al bot primero.")
            return

        user_id, nombre, url, imagen, precio_real = producto
        
        print(f"🎬 Producto encontrado: {nombre[:20]}...")
        print(f"💰 Precio Real: {precio_real}€")
        
        # --- CONFIGURACIÓN DE LA MENTIRA ---
        PRECIO_FALSO_OFERTA = 399.99  # <--- PON AQUÍ EL PRECIO BARATO
        PRECIO_ANTES = precio_real    # El precio real será el "tachado"
        # -----------------------------------

        pct = int(((PRECIO_ANTES - PRECIO_FALSO_OFERTA) / PRECIO_ANTES) * 100)
        
        # Construimos el mensaje IDÉNTICO al del bot original
        caption = (
            f"🚨 <b>BAJADA DETECTADA</b> 🚨\n\n"
            f"📦 <b>{nombre[:40]}...</b>\n"
            f"📉 <b>-{pct}%</b> | <s>{PRECIO_ANTES}€</s> ➡️ <b>{PRECIO_FALSO_OFERTA}€</b>\n"
            f"🏆 <b>¡MÍNIMO HISTÓRICO!</b>\n"
            f"👉 <a href='{url}'>APROVECHAR OFERTA</a>\n"
            f"\n<i>⚠️ Precios sujetos a cambios en Amazon.</i>"
        )
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Ver Gráfica", callback_data="fake_chart")], # Este botón no irá, es atrezzo
            [InlineKeyboardButton(text="🛒 COMPRAR", url=url)]
        ])

        # ENVIAMOS EL MENSAJE
        bot = Bot(token=TOKEN)
        print("🎥 ¡Acción! Enviando alerta falsa en 3 segundos...")
        await asyncio.sleep(3)
        
        if imagen and "http" in imagen:
            await bot.send_photo(user_id, photo=imagen, caption=caption, parse_mode="HTML", reply_markup=kb)
        else:
            await bot.send_message(user_id, caption, parse_mode="HTML", reply_markup=kb)
            
        print("✅ ¡Corten! Mensaje enviado. Espero que lo hayas grabado.")
        await bot.session.close()

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(enviar_alerta_falsa())