import sqlite3
import os
from .config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if not exists."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Skins Table (Usually populated from external API metadata)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS skins (
        id TEXT PRIMARY KEY,
        market_hash_name TEXT,
        collection_id TEXT,
        rarity_rank INTEGER,
        min_float REAL,
        max_float REAL,
        image_url TEXT
    )
    ''')

    # Collections Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS collections (
        id TEXT PRIMARY KEY,
        name TEXT
    )
    ''')

    # Prices Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prices (
        skin_id TEXT,
        condition TEXT,
        is_stattrak INTEGER,
        price REAL,
        sell_num INTEGER,
        goods_id INTEGER PRIMARY KEY,
        updated_at TIMESTAMP,
        predicted_price REAL,
        irregular INTEGER DEFAULT 0,
        FOREIGN KEY(skin_id) REFERENCES skins(id)
    )
    ''')

    # Historical Prices
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS price_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skin_id TEXT,
        condition TEXT,
        is_stattrak INTEGER,
        price REAL,
        recorded_at TIMESTAMP
    )
    ''')
    
    # Migrations
    try:
        cursor.execute("ALTER TABLE prices ADD COLUMN predicted_price REAL")
    except sqlite3.OperationalError: pass
    try:
        cursor.execute("ALTER TABLE prices ADD COLUMN irregular INTEGER DEFAULT 0")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()
