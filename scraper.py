import asyncio
import random
from playwright.async_api import async_playwright
import re
from urllib.parse import urlparse

# --- LISTA ROTATIVA DE AGENTES (Para que Amazon no nos reconozca) ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/118.0.2088.61"
]

async def get_random_ua():
    return random.choice(USER_AGENTS)

async def random_sleep():
    """Espera humana aleatoria para no parecer robot."""
    await asyncio.sleep(random.uniform(1.5, 3.5))

async def get_amazon_price(url):
    async with async_playwright() as p:
        # Usamos un agente aleatorio cada vez
        ua = await get_random_ua()
        browser = await p.chromium.launch(headless=True)
        
        # Añadimos argumentos para evitar detección de bot
        context = await browser.new_context(
            user_agent=ua,
            viewport={'width': 1920, 'height': 1080},
            locale='es-ES'
        )
        page = await context.new_page()

        try:
            # Timeout más largo por seguridad
            await page.goto(url, timeout=90000)
            await random_sleep() # Pausa humana
            
            try: title = await page.inner_text("#productTitle", timeout=5000)
            except: title = "Producto Amazon"

            price, currency = await _extract_price_data(page)

            original_price = price
            try:
                orig_el = page.locator(".a-text-price .a-offscreen").first
                if await orig_el.count() > 0:
                    orig_text = await orig_el.inner_text()
                    original_price = _clean_price_generic(orig_text)
            except: pass
            
            if original_price == 0: original_price = price
            is_deal = price < original_price

            image_url = ""
            try:
                img_el = page.locator("#landingImage, #imgBlkFront, #main-image").first
                if await img_el.count() > 0:
                    image_url = await img_el.get_attribute("src")
                    if not image_url:
                         image_url = await img_el.get_attribute("data-old-hires")
            except: pass

            await browser.close()
            return title.strip(), price, original_price, is_deal, currency, image_url

        except Exception as e:
            print(f"⚠️ Escudo Anti-Bot activado o error: {e}")
            await browser.close()
            return None, 0.0, 0.0, False, "€", ""

async def get_wishlist_items(url):
    items_found = []
    parsed_uri = urlparse(url)
    base_domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}" 

    async with async_playwright() as p:
        ua = await get_random_ua()
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=ua)
        page = await context.new_page()
        
        try:
            print(f"📖 Leyendo Wishlist: {url}")
            await page.goto(url, timeout=90000)
            await random_sleep()
            
            previous_height = 0
            for _ in range(8): 
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(random.uniform(1.5, 3.0)) # Scroll humano
                new_height = await page.evaluate("document.body.scrollHeight")
                if new_height == previous_height: break
                previous_height = new_height
            
            elements = await page.locator("#g-items > li").all()
            
            for el in elements:
                try:
                    link_el = el.locator("h2.a-size-base a, a[id^='itemName_']").first
                    if await link_el.count() == 0: continue 

                    name = await link_el.get_attribute("title")
                    if not name: name = await link_el.inner_text()
                    
                    rel_url = await link_el.get_attribute("href")
                    full_url = base_domain + rel_url.split("?")[0] if rel_url else ""

                    price = 0.0
                    currency = "€"
                    
                    try:
                        sym = await el.locator(".a-price-symbol").first.inner_text()
                        if sym: currency = sym
                    except: pass

                    if await el.locator(".a-price-whole").count() > 0:
                        whole = await el.locator(".a-price-whole").first.inner_text()
                        fraction = "00"
                        if await el.locator(".a-price-fraction").count() > 0:
                            fraction = await el.locator(".a-price-fraction").first.inner_text()
                        whole_clean = re.sub(r'[^\d]', '', whole)
                        price = float(f"{whole_clean}.{fraction}")

                    original_price = price
                    try:
                        strikethrough = el.locator(".a-text-price .a-offscreen, span[style*='line-through']").first
                        if await strikethrough.count() > 0:
                            orig_text = await strikethrough.inner_text()
                            val_orig = _clean_price_generic(orig_text)
                            if val_orig > price: original_price = val_orig
                    except: pass

                    img_url = ""
                    try:
                        img_tag = el.locator("img").first
                        if await img_tag.count() > 0:
                            img_url = await img_tag.get_attribute("src")
                    except: pass

                    if price > 0:
                        items_found.append({
                            "name": name.strip(),
                            "url": full_url,
                            "price": price,
                            "original_price": original_price,
                            "currency": currency.strip(),
                            "image_url": img_url
                        })

                except Exception: continue 

            await browser.close()
            return items_found

        except Exception as e:
            print(f"Error Wishlist: {e}")
            await browser.close()
            return []

# --- HELPERS ---
async def _extract_price_data(page):
    price = 0.0
    currency = "€"
    try:
        sym = page.locator(".a-price-symbol").first
        if await sym.count() > 0: currency = await sym.inner_text()
        whole = await page.locator(".a-price-whole").first.inner_text(timeout=2000)
        fraction = await page.locator(".a-price-fraction").first.inner_text(timeout=500)
        whole_clean = re.sub(r'[^\d]', '', whole)
        price = float(f"{whole_clean}.{fraction}")
    except: pass
    return price, currency.strip()

def _clean_price_generic(text):
    if not text: return 0.0
    text = re.sub(r'[^\d.,]', '', text)
    if "," in text and "." in text:
        if text.find(",") < text.find("."): text = text.replace(",", "")
        else: text = text.replace(".", "").replace(",", ".")
    elif "," in text: text = text.replace(",", ".")
    try: return float(text)
    except: return 0.0

def is_wishlist(url):
    return "wishlist" in url or "registry" in url