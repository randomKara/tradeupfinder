import sys
import os
import json
import sqlite3
from datetime import datetime

# Add root folder to path to allow importing tradeup package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradeup.config import DB_PATH, PRICE_JSON_PATH, OVERRIDES_PATH, RMB_TO_USD_RATE
from tradeup.utils import parse_market_name
from tradeup.database import init_db, get_db_connection
from tradeup.sanitizer import PriceSanitizer

def update_prices():
    # 1. Initialize DB and Tables
    init_db()
    
    if not os.path.exists(PRICE_JSON_PATH):
        print(f"Error: {PRICE_JSON_PATH} not found.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # 2. Parse price.json
    with open(PRICE_JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    items = data if isinstance(data, list) else data.get('goods_list', [])

    print(f"Processing {len(items)} items from market data...")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    updated_count = 0
    for item in items:
        # Simplified parsing for the script
        market_name = item['market_hash_name']
        price = float(item.get('sell_min_price', 0))
        sell_num = item.get('sell_num', 0)
        
        base_name, cond, st = parse_market_name(market_name)
        if not base_name: continue

        cursor.execute("SELECT id FROM skins WHERE market_hash_name = ?", (base_name,))
        res = cursor.fetchone()
        if res:
            skin_id = res['id']
            # Update Current Prices
            cursor.execute('''
                INSERT OR REPLACE INTO prices 
                (skin_id, condition, is_stattrak, price, sell_num, goods_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (skin_id, cond, st, price, sell_num, item['goods_id'], now))
            
            # History
            cursor.execute('''
                INSERT INTO price_history (skin_id, condition, is_stattrak, price, recorded_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (skin_id, cond, st, price, now))
            updated_count += 1

    conn.commit()
    print(f"Sync complete: {updated_count} items updated.")

    # 3. Sanitize and Predict
    print("\nRunning PriceSanitizer...")
    sanitizer = PriceSanitizer(DB_PATH)
    sanitizer.load_data()
    sanitizer.build_collection_stats()
    sanitizer.build_global_regression()
    
    anomalies = sanitizer.detect_anomalies()
    print(f"Detection complete: {len(anomalies)} anomalies found.")

    # Update DB with predictions
    updates = []
    for (skin_id, cond, is_st), real_p in sanitizer.prices.items():
        predicted = sanitizer.get_predicted_price(skin_id, cond, is_st)
        if predicted:
            updates.append((round(predicted / RMB_TO_USD_RATE, 2), skin_id, cond, is_st))

    cursor.executemany("UPDATE prices SET predicted_price = ? WHERE skin_id = ? AND condition = ? AND is_stattrak = ?", updates)
    
    # Flag Irregular
    cursor.execute("UPDATE prices SET irregular = 0")
    name_to_id = {v['market_hash_name']: k for k, v in sanitizer.skins.items()}
    irreg_updates = []
    for a in anomalies:
        sid = name_to_id.get(a['skin'])
        if sid: irreg_updates.append((sid, a['condition'], 1 if a['is_stattrak'] else 0))
    
    cursor.executemany("UPDATE prices SET irregular = 1 WHERE skin_id = ? AND condition = ? AND is_stattrak = ?", irreg_updates)
    
    conn.commit()
    conn.close()
    print("Database fully sanitized and updated.")

if __name__ == "__main__":
    update_prices()
