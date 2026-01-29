import sqlite3
import json
import os
import re
from datetime import datetime

# --- CONFIGURATION ---
DB_NAME = "cs2_skins.db"
PRICE_FILE = "price.json"

# Mapping des conditions Buff -> Nos abréviations
CONDITION_MAP = {
    "Factory New": "FN",
    "Minimal Wear": "MW",
    "Field-Tested": "FT",
    "Well-Worn": "WW",
    "Battle-Scarred": "BS"
}

def init_price_tables(cursor):
    """Crée les tables de prix et d'historique"""
    # Table des prix actuels (Dernier état connu)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS prices (
        skin_id TEXT,
        condition TEXT,
        is_stattrak INTEGER,
        price REAL,
        sell_num INTEGER,
        goods_id INTEGER PRIMARY KEY,
        updated_at TIMESTAMP,
        FOREIGN KEY(skin_id) REFERENCES skins(id)
    )
    ''')

    # Table historique (Pour l'analyse de tendance)
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

def parse_market_name(full_name):
    """
    Sépare le nom en : Nom propre, Condition, Is_StatTrak
    Ex: "StatTrak™ AWP | Exothermic (Well-Worn)" 
    -> ("AWP | Exothermic", "WW", 1)
    """
    # 1. Exclusion des Souvenirs
    if "Souvenir" in full_name:
        return None, None, None

    # 2. Détection StatTrak
    is_stattrak = 1 if "StatTrak™" in full_name else 0
    
    # Nettoyage du nom pour enlever les tags
    clean_name = full_name.replace("StatTrak™ ", "")
    
    # 3. Extraction de la condition entre parenthèses
    # Cherche ce qu'il y a dans la dernière parenthèse
    match = re.search(r'\((.*?)\)$', clean_name)
    if not match:
        return None, None, None
        
    buff_condition = match.group(1)
    condition_code = CONDITION_MAP.get(buff_condition)
    
    if not condition_code:
        return None, None, None

    # 4. Le nom du skin est ce qui reste avant la parenthèse
    # On enlève l'espace avant la parenthèse
    skin_base_name = clean_name.replace(f" ({buff_condition})", "").strip()
    
    return skin_base_name, condition_code, is_stattrak
def parse_market_name(full_name):
    if "Souvenir" in full_name:
        return None, None, None

    is_stattrak = 1 if "StatTrak™" in full_name else 0
    clean_name = full_name.replace("StatTrak™ ", "")

    # Regex plus robuste qui cherche la condition UNIQUEMENT à la toute fin du string
    # Elle capture : (Espace)(Parenthèse)(Condition)(Parenthèse)(Fin de ligne)
    pattern = r'\s\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$'
    match = re.search(pattern, clean_name)
    
    if not match:
        return None, None, None
        
    buff_condition = match.group(1)
    # Le nom du skin est TOUT ce qui précède la condition
    skin_base_name = clean_name[:match.start()].strip()
    
    # --- GESTION DES DOPPLERS & PHASES ---
    # Si le nom contient (Phase X) ou (Emerald/Ruby/etc), on le nettoie aussi 
    # pour matcher avec la base ByMykel qui est générique.
    phase_pattern = r'\s\((Phase \d|Emerald|Ruby|Sapphire|Black Pearl)\)$'
    skin_base_name = re.sub(phase_pattern, "", skin_base_name).strip()

    return skin_base_name, CONDITION_MAP.get(buff_condition), is_stattrak

def update_prices():
    if not os.path.exists(PRICE_FILE):
        print(f"Erreur : {PRICE_FILE} non trouvé.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    init_price_tables(cursor)

    with open(PRICE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    items = data.get('info', []) # Note: l'API Buff renvoie souvent 'items' ou 'items_list'
    if not items:
        # Si le JSON est juste une liste d'objets (comme ton extrait)
        items = data if isinstance(data, list) else data.get('goods_list', [])

    print(f"Traitement de {len(items)} items...")
    
    updated_count = 0
    skipped_count = 0
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for item in items:
        goods_id = item['goods_id']
        market_name = item['market_hash_name']
        
        # Récupération du prix (Buff met souvent le prix dans 'sales' -> 'min_price')
        price = 0
        if 'sales' in item and len(item['sales']) > 0:
            price = float(item['sales'][0]['min_price'])
        else:
            price = float(item.get('sell_min_price', 0))

        # Récupération du volume (si disponible)
        sell_num = item.get('sell_num', 0)
        if 'sales' in item and len(item['sales']) > 0:
            sell_num = item['sales'][0].get('sell_num', sell_num)

        # Parsing du nom pour matcher avec notre DB statique
        base_name, cond, st = parse_market_name(market_name)
        
        if not base_name:
            skipped_count += 1
            continue

        # Trouver le skin_id correspondant dans notre table 'skins'
        cursor.execute("SELECT id FROM skins WHERE market_hash_name = ?", (base_name,))
        result = cursor.fetchone()
        
        if result:
            skin_id = result[0]
            
            # 1. Mise à jour table 'prices' (Prix actuel)
            cursor.execute('''
                INSERT OR REPLACE INTO prices 
                (skin_id, condition, is_stattrak, price, sell_num, goods_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (skin_id, cond, st, price, sell_num, goods_id, now))

            # 2. Ajout à l'historique
            cursor.execute('''
                INSERT INTO price_history (skin_id, condition, is_stattrak, price, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (skin_id, cond, st, price, now))
            
            updated_count += 1
        else:
            # Cas où le skin Buff n'existe pas dans l'API ByMykel (ex: stickers, caisses)
            skipped_count += 1

    conn.commit()
    conn.close()
    print(f"Mise à jour terminée.")
    print(f"Items synchronisés : {updated_count}")
    print(f"Items ignorés (souvenirs, caisses, etc.) : {skipped_count}")

if __name__ == "__main__":
    update_prices()