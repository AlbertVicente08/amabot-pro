import aiosqlite
from datetime import datetime

DB_NAME = "bot_chollos.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                categories TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_url TEXT,
                product_name TEXT,
                target_price REAL, 
                current_price REAL,
                min_price REAL,
                image_url TEXT,
                is_wishlist BOOLEAN DEFAULT 0
            )
        ''')
        # NUEVA TABLA: HISTORIAL DE PRECIOS
        await db.execute('''
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id INTEGER,
                price REAL,
                date_time TEXT
            )
        ''')
        await db.commit()

async def add_user(user_id, username, category=""):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, categories) VALUES (?, ?, ?)", 
                         (user_id, username, category))
        await db.commit()

async def add_product(user_id, url, name, price, image_url="", is_wishlist=False):
    async with aiosqlite.connect(DB_NAME) as db:
        # 1. Insertamos producto
        cursor = await db.execute("SELECT id FROM tracking WHERE user_id = ? AND product_url = ?", (user_id, url))
        row = await cursor.fetchone()
        
        if row:
            tracking_id = row[0]
        else:
            cursor = await db.execute('''
                INSERT INTO tracking (user_id, product_url, product_name, target_price, current_price, min_price, image_url, is_wishlist)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, url, name, price, price, price, image_url, is_wishlist))
            tracking_id = cursor.lastrowid
        
        # 2. Guardamos el primer punto del historial
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        await db.execute("INSERT INTO price_history (tracking_id, price, date_time) VALUES (?, ?, ?)", 
                         (tracking_id, price, timestamp))
        await db.commit()

async def update_product_price(product_id, new_price):
    async with aiosqlite.connect(DB_NAME) as db:
        # Actualizamos tabla principal
        cursor = await db.execute("SELECT min_price FROM tracking WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        if row:
            old_min = row[0]
            new_min = new_price if new_price < old_min else old_min
            await db.execute("UPDATE tracking SET current_price = ?, min_price = ? WHERE id = ?", 
                             (new_price, new_min, product_id))
            
            # GUARDAMOS HISTORIAL (Solo si el precio cambia para no llenar la BD de datos iguales, o cada hora si prefieres)
            # Para que la gráfica se vea bonita, guardamos cada punto revisado:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            await db.execute("INSERT INTO price_history (tracking_id, price, date_time) VALUES (?, ?, ?)", 
                             (product_id, new_price, timestamp))
            
            await db.commit()

async def get_price_history(tracking_id):
    """Recupera los datos para la gráfica."""
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT price, date_time FROM price_history WHERE tracking_id = ? ORDER BY id ASC", (tracking_id,))
        return await cursor.fetchall()

async def get_user_products(user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tracking WHERE user_id = ? ORDER BY id DESC", (user_id,))
        return await cursor.fetchall()

async def delete_product(product_id, user_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tracking WHERE id = ? AND user_id = ?", (product_id, user_id))
        # Opcional: Borrar historial también
        await db.execute("DELETE FROM price_history WHERE tracking_id = ?", (product_id,))
        await db.commit()

async def get_top_deals(limit=5):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        query = '''
            SELECT product_name, product_url, target_price, current_price, image_url,
            (target_price - current_price) as ahorro,
            ((target_price - current_price) / target_price * 100) as porcentaje
            FROM tracking 
            WHERE current_price < target_price
            ORDER BY porcentaje DESC
            LIMIT ?
        '''
        cursor = await db.execute(query, (limit,))
        return await cursor.fetchall()