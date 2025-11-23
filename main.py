import asyncio
import logging
import html
import random
import io
import matplotlib.pyplot as plt
import traceback
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
scheduler = AsyncIOScheduler()
plt.switch_backend('Agg')

# --- UTILS ---
def monetizar_url(url):
    """
    Añade el tag de afiliado de forma segura conservando otros parámetros.
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")
        tag = AFFILIATE_TAGS.get(domain)
        if not tag: return url
        
        # Obtenemos parámetros actuales y añadimos el tag
        query_params = dict(parse_qsl(parsed.query))
        query_params["tag"] = tag
        
        # Reconstruimos URL
        new_query = urlencode(query_params)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
    except: return url

def generar_barra(progreso, total=10):
    llenos = int(progreso / 100 * total)
    vacios = total - llenos
    return "█" * llenos + "▒" * vacios

async def animar_espera(mensaje_bot, texto_base):
    try:
        etapas = [10, 30, 55, 75, 90]
        for p in etapas:
            barra = generar_barra(p)
            txt = f"⏳ <b>{texto_base}</b>\n\n[{barra}] {p}%"
            await mensaje_bot.edit_text(txt, parse_mode="HTML")
            await asyncio.sleep(random.uniform(0.3, 0.8))
    except: pass

def get_main_buttons():
    link_amazon = monetizar_url("https://www.amazon.es")
    return [
        [InlineKeyboardButton(text="🎒 Mis Chollos", callback_data="cmd_my_items"),
         InlineKeyboardButton(text="🔥 Populares", callback_data="cmd_top_deals")],
        [InlineKeyboardButton(text="🛒 Ir a Amazon", url=link_amazon),
         InlineKeyboardButton(text="❓ Ayuda", callback_data="cmd_help")]
    ]

async def generar_grafica_imagen(tracking_id, product_name):
    history = await database.get_price_history(tracking_id)
    if not history or len(history) < 2: return None
    precios = [h[0] for h in history]
    fechas = [h[1].split(" ")[0] for h in history]
    
    plt.figure(figsize=(10, 5))
    plt.plot(fechas, precios, marker='o', linestyle='-', color='#ff9900', linewidth=2)
    plt.title(f"Historial: {product_name[:30]}...", fontsize=14)
    plt.xlabel("Fecha")
    plt.ylabel("Precio (€)")
    plt.grid(True, linestyle='--', alpha=0.7)
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

# --- VIGILANTE ---
async def check_price_updates():
    print("⏰ Cron: Revisando precios...")
    products = []
    try:
        async with database.aiosqlite.connect(database.DB_NAME) as db:
            cursor = await db.execute("SELECT id, user_id, product_url, product_name, current_price, min_price, image_url FROM tracking")
            products = await cursor.fetchall()
    except Exception as e:
        print(f"❌ Error DB: {e}")
        return

    if not products:
        print("📭 Base de datos vacía.")
        return

    print(f"📋 Revisando {len(products)} productos...")

    for prod in products:
        prod_id, user_id, url, name, last_price, historic_min, image_url = prod
        
        try:
            # Scraper devuelve 7 valores ahora (con final_url)
            data = await asyncio.wait_for(scraper.get_amazon_price(url), timeout=40)
            if not data: continue
            _, new_price, _, _, currency, _, final_url = data # Usamos final_url para monetizar si ha cambiado
        except Exception as e:
            print(f"⚠️ Skip {url}: {e}")
            continue
        
        if new_price > 0:
            await database.update_product_price(prod_id, new_price)
            
            if new_price < (last_price - 0.05):
                if last_price == 0: last_price = new_price + 1
                pct = int(((last_price - new_price) / last_price) * 100)
                txt_rec = "🏆 <b>¡MÍNIMO HISTÓRICO!</b>" if new_price < historic_min else ""
                link = monetizar_url(final_url) # Monetizamos la URL final resuelta
                safe_name = html.escape(name)

                print(f"🚨 BAJADA DETECTADA: {name[:10]}... (-{pct}%)")
                legal_footer = "\n<i>⚠️ Precios sujetos a cambios en Amazon.</i>"

                # PRIVADO
                caption_private = (
                    f"🚨 <b>BAJADA DETECTADA</b> 🚨\n\n"
                    f"📦 <b>{safe_name[:40]}...</b>\n"
                    f"📉 <b>-{pct}%</b> | <s>{last_price}{currency}</s> ➡️ <b>{new_price}{currency}</b>\n"
                    f"{txt_rec}\n"
                    f"👉 <a href='{link}'>APROVECHAR OFERTA</a>"
                    f"{legal_footer}"
                )
                kb_private = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📊 Ver Gráfica", callback_data=f"chart_{prod_id}")],
                    [InlineKeyboardButton(text="🛒 COMPRAR", url=link)]
                ])
                try:
                    if image_url and "http" in image_url:
                        await bot.send_photo(user_id, photo=image_url, caption=caption_private, parse_mode="HTML", reply_markup=kb_private)
                    else:
                        await bot.send_message(user_id, caption_private, parse_mode="HTML", reply_markup=kb_private)
                except: pass

                # PÚBLICO
                if pct >= MIN_DISCOUNT_TO_POST:
                    caption_public = (
                        f"🔥 <b>¡CHOLLAZO DETECTADO! -{pct}%</b> 🔥\n\n"
                        f"📦 <b>{safe_name}</b>\n"
                        f"📉 De <s>{last_price}{currency}</s> a <b>{new_price}{currency}</b>\n\n"
                        f"🏃‍♂️ <b>¡Corre antes de que se agote!</b>\n"
                        f"👉 <a href='{link}'>VER EN AMAZON</a>"
                        f"{legal_footer}"
                    )
                    kb_public = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🛒 COMPRAR AHORA ({new_price}{currency})", url=link)]])
                    try:
                        if image_url and "http" in image_url:
                            await bot.send_photo(chat_id=PUBLIC_CHANNEL, photo=image_url, caption=caption_public, parse_mode="HTML", reply_markup=kb_public)
                        else:
                            await bot.send_message(chat_id=PUBLIC_CHANNEL, text=caption_public, parse_mode="HTML", reply_markup=kb_public)
                    except Exception as e: print(f"❌ Error canal: {e}")

# --- COMANDOS ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await database.init_db()
    await database.add_user(message.from_user.id, html.escape(message.from_user.first_name))
    kb = InlineKeyboardMarkup(inline_keyboard=get_main_buttons())
    legal_text = "\n\n⚖️ <i>Afiliado de Amazon: Gano ingresos por compras adscritas.</i>"
    await message.answer(
        f"👋 <b>¡Hola! Soy Amabot.</b>\n\n"
        "1️⃣ Envíame un enlace o Wishlist.\n"
        "2️⃣ Te avisaré con FOTO y GRÁFICA.\n"
        "3️⃣ Busco las mejores ofertas 24/7."
        f"{legal_text}",
        reply_markup=kb, parse_mode="HTML"
    )

@dp.callback_query(F.data == "cmd_my_items")
async def cb_my(c: CallbackQuery):
    await show_user_items(c.from_user.id, c.message)
    await c.answer()

@dp.callback_query(F.data == "cmd_top_deals")
async def cb_top(c: CallbackQuery):
    await show_top_deals(c.message)
    await c.answer()

@dp.callback_query(F.data == "cmd_help")
async def cb_help(c: CallbackQuery):
    await c.message.answer("❓ Pega el link de Amazon.", parse_mode="HTML")
    await c.answer()

@dp.callback_query(F.data.startswith("del_"))
async def cb_del(c: CallbackQuery):
    try:
        pid = int(c.data.split("_")[1])
        await database.delete_product(pid, c.from_user.id)
        await c.message.delete()
        await c.answer("🗑️ Eliminado")
    except: await c.answer("Error")

# --- NUEVO: BORRAR TODO ---
@dp.callback_query(F.data == "del_all")
async def cb_del_all(c: CallbackQuery):
    try:
        await database.delete_all_products(c.from_user.id)
        # Volvemos al menú principal
        kb = InlineKeyboardMarkup(inline_keyboard=get_main_buttons())
        await c.message.edit_text("🗑️ <b>Todos tus productos han sido borrados.</b>", parse_mode="HTML", reply_markup=kb)
    except Exception as e:
        print(e)
        await c.answer("Error borrando")

@dp.callback_query(F.data.startswith("chart_"))
async def cb_chart(c: CallbackQuery):
    try:
        pid = int(c.data.split("_")[1])
        await c.answer("🎨 Generando gráfica...")
        buf = await generar_grafica_imagen(pid, "Producto")
        if buf:
            photo = BufferedInputFile(buf.read(), filename="chart.png")
            await c.message.answer_photo(photo, caption="📊 <b>Historial de Precios</b>", parse_mode="HTML")
        else:
            await c.message.answer("📉 <b>Faltan datos.</b>", parse_mode="HTML")
    except: await c.answer("Error")

# --- VISUALES ---
async def show_user_items(user_id, message_obj):
    items = await database.get_user_products(user_id)
    menu_principal = get_main_buttons()

    if not items:
        kb = InlineKeyboardMarkup(inline_keyboard=menu_principal)
        await message_obj.answer("📭 <b>Vacío.</b>", parse_mode="HTML", reply_markup=kb)
        return

    # Botón BORRAR TODO al principio
    kb_borrar_todo = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ BORRAR TODO MI RASTREO", callback_data="del_all")]
    ])
    await message_obj.answer(f"🎒 <b>TUS PRODUCTOS ({len(items)})</b>", parse_mode="HTML", reply_markup=kb_borrar_todo)
    
    for item in items[:5]: 
        safe_name = html.escape(item['product_name'])
        link = monetizar_url(item['product_url'])
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Gráfica", callback_data=f"chart_{item['id']}")],
            [InlineKeyboardButton(text="🔗 Amazon", url=link),
             InlineKeyboardButton(text="🗑️ Borrar", callback_data=f"del_{item['id']}")]
        ])
        txt = f"🔹 <b>{safe_name[:35]}...</b>\n💰 <b>{item['current_price']}€</b>"
        img = item['image_url']
        try:
            if img and "http" in img:
                await message_obj.answer_photo(photo=img, caption=txt, parse_mode="HTML", reply_markup=kb)
            else:
                await message_obj.answer(txt, parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)
            await asyncio.sleep(0.2)
        except: pass
    
    kb_menu = InlineKeyboardMarkup(inline_keyboard=menu_principal)
    await message_obj.answer("👇 <b>Menú:</b>", reply_markup=kb_menu, parse_mode="HTML")

async def show_top_deals(message_obj):
    deals = await database.get_top_deals(5)
    menu_principal = get_main_buttons()
    
    if not deals:
        kb = InlineKeyboardMarkup(inline_keyboard=menu_principal)
        await message_obj.answer("😴 <b>Sin ofertas aún.</b>", parse_mode="HTML", reply_markup=kb)
        return
        
    await message_obj.answer("🔥 <b>TOP OFERTAS GLOBALES</b> 🔥", parse_mode="HTML")
    for d in deals:
        pct = int(d['porcentaje'])
        link = monetizar_url(d['product_url'])
        safe = html.escape(d['product_name'])
        img = d['image_url']
        oferta_txt = f"💣 <b>-{pct}%</b> " if pct > 0 else "💎 "
        caption = f"{oferta_txt}<b>{safe[:30]}...</b>\n➡️ <b>{d['current_price']}€</b> <s>{d['target_price']}€</s>"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"🛒 VER OFERTA", url=link)]])
        try:
            if img and "http" in img:
                await message_obj.answer_photo(photo=img, caption=caption, parse_mode="HTML", reply_markup=kb)
            else:
                await message_obj.answer(caption, parse_mode="HTML", reply_markup=kb)
        except: pass
    kb_menu = InlineKeyboardMarkup(inline_keyboard=menu_principal)
    await message_obj.answer("👇 <b>Menú:</b>", reply_markup=kb_menu, parse_mode="HTML")

# --- CORE ---
@dp.message() 
async def handle_message(message: types.Message):
    text = message.text
    user_id = message.from_user.id
    
    if "amazon" not in text.lower() and "amzn" not in text.lower():
        kb = InlineKeyboardMarkup(inline_keyboard=get_main_buttons())
        await message.answer("👇 <b>Menú Principal:</b>", reply_markup=kb, parse_mode="HTML")
        return
    
    status_msg = await message.answer("⏳ <b>Iniciando...</b>\n[▒▒▒▒▒▒▒▒▒▒] 0%", parse_mode="HTML")
    anim_task = asyncio.create_task(animar_espera(status_msg, "Analizando..."))
    
    try:
        # === WISHLIST ===
        if scraper.is_wishlist(text):
            items = await scraper.get_wishlist_items(text)
            anim_task.cancel()
            
            if not items:
                await status_msg.edit_text("❌ <b>Error.</b> Lista privada.", parse_mode="HTML")
                return

            reporte = f"🛍️ <b>LISTA ({len(items)})</b>\n━━━━━━━━━━━━━━━━━\n\n"
            botones_producto = []
            for i, item in enumerate(items):
                img_u = item.get('image_url', '')
                await database.add_product(user_id, item['url'], item['name'], item['price'], image_url=img_u, is_wishlist=True)
                
                moneda = item.get('currency', '€')
                actual = item['price']
                original = item.get('original_price', actual)
                safe_name = html.escape(item['name'])
                link_money = monetizar_url(item['url']) # Link monetizado

                if original > actual:
                    pct = int((original - actual) / original * 100)
                    icono = "🔥"
                    linea = f"<b>{actual}{moneda}</b> <s>{original}</s> (-{pct}%)"
                else:
                    icono = "🔹"
                    linea = f"<b>{actual}{moneda}</b>"

                reporte += f"{icono} {safe_name[:20]}...\n└ {linea}\n\n"
                if i < 5:
                    btn_txt = f"{i+1}. Ver {actual}{moneda}"
                    if original > actual: btn_txt += " 🔥"
                    botones_producto.append([InlineKeyboardButton(text=btn_txt, url=link_money)])

            reporte += "✅ <b>Vigilando 24/7.</b>"
            botones_finales = botones_producto
            botones_finales.extend(get_main_buttons())
            kb_list = InlineKeyboardMarkup(inline_keyboard=botones_finales)
            await status_msg.edit_text(reporte, parse_mode="HTML", reply_markup=kb_list, disable_web_page_preview=True)

        # === PRODUCTO SUELTO ===
        else:
            # Scraper devuelve 7 valores
            data = await scraper.get_amazon_price(text)
            anim_task.cancel()
            
            if data and data[1] > 0:
                title, price, original_price, is_deal, currency, image_url, final_url = data
                
                # Guardamos la URL FINAL para evitar acortadores
                await database.add_product(user_id, final_url, title, price, image_url=image_url)
                
                link_money = monetizar_url(final_url)
                safe_title = html.escape(title)
                
                vis = ""
                if is_deal and original_price > price:
                    pct = int(100 - (price / original_price * 100))
                    vis = f"\n🔥 <b>-{pct}%</b> (<s>{original_price}{currency}</s>)"

                caption = (
                    f"✅ <b>GUARDADO</b>\n━━━━━━━━━━━━━━━━━\n"
                    f"📦 <b>{safe_title}</b>\n"
                    f"🏷 <b>{price}{currency}</b>{vis}\n"
                    f"━━━━━━━━━━━━━━━━━"
                )
                
                botones = [[InlineKeyboardButton(text="🛒 VER EN AMAZON", url=link_money)]]
                botones.extend(get_main_buttons())
                kb = InlineKeyboardMarkup(inline_keyboard=botones)
                
                await status_msg.delete()
                if image_url and "http" in image_url:
                    await message.answer_photo(photo=image_url, caption=caption, parse_mode="HTML", reply_markup=kb)
                else:
                    await message.answer(caption, parse_mode="HTML", reply_markup=kb)
            else:
                await status_msg.edit_text("⚠️ No pude leer el precio.")

    except Exception as e:
        anim_task.cancel()
        print(f"ERROR: {e}")
        traceback.print_exc()
        await status_msg.edit_text("❌ Error inesperado.")

async def main():
    print("🤖 BOT FINAL (ANTI-CORTOS + BORRAR TODO) INICIADO...")
    await database.init_db()
    scheduler.add_job(check_price_updates, 'interval', minutes=60) 
    scheduler.start()
    print("🚀 Forzando revisión inicial...")
    await check_price_updates()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot apagado manualmente.")
    except Exception:
        print("❌ ¡ERROR CRÍTICO DETECTADO!")
        traceback.print_exc()