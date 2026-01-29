import sqlite3
import requests
import os
import json

# --- CONFIGURATION ---
DB_NAME = "cs2_skins.db"
# URL brute du fichier JSON de ByMykel (contient tous les skins)
API_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"

# Mapping des raretés pour faciliter les calculs (1 = Gris ... 6 = Rouge)
RARITY_MAP = {
    "Consumer Grade": 1,
    "Industrial Grade": 2,
    "Mil-Spec Grade": 3,
    "Restricted": 4,
    "Classified": 5,
    "Covert": 6,
    "Contraband": 7 # Sera exclu
}

def create_schema(cursor):
    """Création des tables statiques"""
    print("Creation du schema de base de donnees...")
    
    # Table Collections
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS collections (
        id TEXT PRIMARY KEY,
        name TEXT
    )
    ''')

    # Table Skins (Données Statiques)
    # On ajoute 'rarity_id' pour trier facilement plus tard
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS skins (
        id TEXT PRIMARY KEY,
        market_hash_name TEXT,
        collection_id TEXT,
        rarity_name TEXT,
        rarity_rank INTEGER,
        min_float REAL,
        max_float REAL,
        FOREIGN KEY(collection_id) REFERENCES collections(id)
    )
    ''')

def fetch_and_populate(connection):
    """Récupération et insertion des données"""
    print(f"Telechargement des donnees depuis {API_URL} ...")
    
    try:
        response = requests.get(API_URL)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Erreur lors du telechargement : {e}")
        return

    cursor = connection.cursor()
    
    skins_count = 0
    collections_cache = set() # Pour éviter de réinsérer les collections
    
    print("Traitement des données...")
    
    for item in data:
        # 1. Filtres de base
        # On ignore les gants, les agents, les couteaux (sauf s'ils sont dans une collection d'armes)
        # Mais surtout on ignore ce qui n'a pas de collection (non trade-upable)
        if "collections" not in item or not item["collections"]:
            continue
            
        rarity_obj = item.get("rarity", {})
        rarity_name = rarity_obj.get("name")
        
        # Exclusion Contraband (Howl)
        if rarity_name == "Contraband":
            continue

        # Exclusion des items sans float (Graffiti, etc.)
        if "min_float" not in item or "max_float" not in item:
            continue

        # 2. Gestion de la Collection
        # Un skin peut être dans plusieurs collections (rare), on prend la première pour le trade up principal
        coll_data = item["collections"][0]
        coll_id = coll_data["id"]
        coll_name = coll_data["name"]
        
        # Insertion Collection (Si pas déjà fait)
        if coll_id not in collections_cache:
            cursor.execute('INSERT OR IGNORE INTO collections (id, name) VALUES (?, ?)', (coll_id, coll_name))
            collections_cache.add(coll_id)

        # 3. Préparation Skin
        skin_id = item["id"]
        name = item["name"] # C'est le nom propre "AK-47 | Slate"
        min_float = item["min_float"]
        max_float = item["max_float"]
        
        # Calcul du rang de rareté
        rank = RARITY_MAP.get(rarity_name, 0)
        
        # On ne garde que les armes (Rank > 0)
        if rank == 0:
            continue

        # 4. Insertion Skin
        cursor.execute('''
        INSERT OR REPLACE INTO skins 
        (id, market_hash_name, collection_id, rarity_name, rarity_rank, min_float, max_float)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (skin_id, name, coll_id, rarity_name, rank, min_float, max_float))
        
        skins_count += 1

    connection.commit()
    print(f"Termine ! {skins_count} skins importes et {len(collections_cache)} collections creees.")

def main():
    # Suppression de l'ancienne DB pour repartir propre si besoin
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
        
    conn = sqlite3.connect(DB_NAME)
    create_schema(conn.cursor())
    fetch_and_populate(conn)
    conn.close()

if __name__ == "__main__":
    main()