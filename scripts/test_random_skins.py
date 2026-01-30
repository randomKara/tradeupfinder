import sqlite3
import random
from pricing_box import predict_price

DB_PATH = "data/cs2_skins.db"

def get_random_skins(limit=3):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get skins that have prices across most conditions to be interesting
    cursor.execute("""
        SELECT s.*, count(p.condition) as price_count
        FROM skins s
        JOIN prices p ON s.id = p.skin_id
        WHERE p.is_stattrak = 0
        GROUP BY s.id
        HAVING price_count >= 3
        ORDER BY RANDOM()
        LIMIT ?
    """, (limit,))
    
    skins = [dict(row) for row in cursor.fetchall()]
    
    results = []
    for skin in skins:
        cursor.execute("SELECT condition, price FROM prices WHERE skin_id = ? AND is_stattrak = 0", (skin['id'],))
        prices = {row['condition']: row['price'] for row in cursor.fetchall()}
        
        # Ensure standard keys are present (even if None)
        base_prices = {cond: prices.get(cond) for cond in ["FN", "MW", "FT", "WW", "BS"]}
        
        results.append({
            "skin": skin,
            "base_prices": base_prices
        })
    
    conn.close()
    return results

def test_skin_pricing(skin_data):
    skin = skin_data['skin']
    bp = skin_data['base_prices']
    
    print(f"\nTarget Skin: {skin['market_hash_name']}")
    print(f"Rarity Rank: {skin['rarity_rank']} | Range: [{skin['min_float']}, {skin['max_float']}]")
    print(f"Base Prices (RMB): {bp}")
    
    # Define test floats across conditions
    # We'll pick 5 points: 0.01, 0.07, 0.15, 0.38, 0.8
    test_floats = [0.01, 0.05, 0.07, 0.10, 0.15, 0.25, 0.38, 0.42, 0.8]
    
    print(f"{'Float':<10} | {'Adj Float':<10} | {'Predicted Price':<15}")
    print("-" * 45)
    
    for f in test_floats:
        # Check if float is within skin range
        if f < skin['min_float'] or f > skin['max_float']:
            continue
            
        pred = predict_price(
            target_real_float=f,
            skin_min=skin['min_float'],
            skin_max=skin['max_float'],
            base_prices=bp,
            rarity=str(skin['rarity_rank']),
            is_st=0
        )
        
        adj = (f - skin['min_float']) / (skin['max_float'] - skin['min_float'])
        print(f"{f:<10.4f} | {adj:<10.4f} | {pred:<15.2f}")

if __name__ == "__main__":
    sample = get_random_skins(3)
    for s in sample:
        test_skin_pricing(s)
