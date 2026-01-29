import sqlite3

# --- CONFIGURATION ---
DB_NAME = "cs2_skins.db"
STEAM_FEE = 0.975          
MIN_ROI = 10.0            
MIN_INPUT_ADJ_FLOAT = 0.20 
MIN_OUTPUT_PRICE = 40.0    
MAX_OUTPUT_PRICE = 5000.0 

# --- RÉGLAGES AVANCÉS ---
ENABLE_STATTRAK = False    # Changez en True pour inclure les StatTrak
FT_PENALTY_MAX_RATIO = 0.8 # À 0.151, on ajoute 80% de la diff FT/MW

def get_condition_code(f):
    if f < 0.07: return "FN"
    if f < 0.15: return "MW"
    if f < 0.38: return "FT"
    if f < 0.45: return "WW"
    return "BS"

def calculate_premium_price(real_f, base_price, skin_prices):
    """
    Simule l'overpay pour les low floats en FT.
    Si FT et float < 0.38, on ajoute une partie de la différence avec le prix MW.
    """
    cond = get_condition_code(real_f)
    
    if cond == "FT" and real_f < 0.38:
        price_mw = skin_prices.get("MW")
        if price_mw and price_mw > base_price:
            # Calcul de la progression entre 0.38 (0%) et 0.15 (100%)
            # factor sera proche de 1.0 si real_f est proche de 0.15
            factor = (0.38 - real_f) / (0.38 - 0.15)
            factor = max(0, min(1, factor)) # Sécurité
            
            penalty = (price_mw - base_price) * (factor * FT_PENALTY_MAX_RATIO)
            return base_price + penalty
            
    return base_price

def calculate_thresholds(outputs):
    thresholds = {0.0699, 0.1499, 0.3799, 0.4499} 
    for skin in outputs:
        if skin['max_price'] > MAX_OUTPUT_PRICE or skin['max_price'] < MIN_OUTPUT_PRICE:
            return None
        r_min, r_max = skin['min_float'], skin['max_float']
        r_range = r_max - r_min
        if r_range <= 0: continue
        for border in [0.07, 0.15, 0.38, 0.45]:
            adj_f = (border - r_min) / r_range
            if 0 < adj_f < 1:
                thresholds.add(round(adj_f - 0.0001, 5))
    return sorted(list(thresholds))

def run_scanner():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM collections")
    collections = cursor.fetchall()

    # Gestion réversible des StatTrak
    st_list = [0, 1] if ENABLE_STATTRAK else [0]

    for coll in collections:
        for rarity_rank in range(1, 6):
            for is_st in st_list:
                # Inputs
                cursor.execute("""
                    SELECT s.* FROM skins s
                    JOIN prices p ON s.id = p.skin_id
                    WHERE s.collection_id = ? AND s.rarity_rank = ? AND p.is_stattrak = ?
                    GROUP BY s.id
                """, (coll['id'], rarity_rank, is_st))
                inputs = [dict(row) for row in cursor.fetchall()]
                
                # Outputs
                cursor.execute("""
                    SELECT s.*, MAX(p.price) as max_price
                    FROM skins s
                    JOIN prices p ON s.id = p.skin_id
                    WHERE s.collection_id = ? AND s.rarity_rank = ? + 1 AND p.is_stattrak = ?
                    GROUP BY s.id
                """, (coll['id'], rarity_rank, is_st))
                outputs = [dict(row) for row in cursor.fetchall()]

                if not inputs or not outputs: continue

                magic_floats = calculate_thresholds(outputs)
                if magic_floats is None: continue 

                # Prix
                cursor.execute("SELECT skin_id, condition, price FROM prices WHERE is_stattrak = ?", (is_st,))
                all_prices = {}
                for row in cursor.fetchall():
                    sid = row['skin_id']
                    if sid not in all_prices: all_prices[sid] = {}
                    all_prices[sid][row['condition']] = row['price']

                for inp in inputs:
                    inp_prices = all_prices.get(inp['id'], {})
                    
                    for adj_target in magic_floats:
                        if adj_target < MIN_INPUT_ADJ_FLOAT: continue

                        real_f = inp['min_float'] + (adj_target * (inp['max_float'] - inp['min_float']))
                        buy_cond = get_condition_code(real_f)
                        base_buy_price = inp_prices.get(buy_cond, 0)
                        
                        if base_buy_price <= 0: continue
                        
                        # APPLICATION DE LA PÉNALITÉ FT
                        buy_price = calculate_premium_price(real_f, base_buy_price, inp_prices)
                        
                        total_cost = buy_price * 10
                        total_ev = 0
                        drop_table = []

                        for out in outputs:
                            out_f = out['min_float'] + (adj_target * (out['max_float'] - out['min_float']))
                            out_cond = get_condition_code(out_f)
                            res_price = all_prices.get(out['id'], {}).get(out_cond, 0)
                            
                            net_res_price = res_price * STEAM_FEE
                            total_ev += net_res_price * (1.0 / len(outputs))
                            
                            individual_profit = net_res_price - total_cost
                            
                            drop_table.append({
                                'name': out['market_hash_name'],
                                'cond': out_cond,
                                'val': net_res_price,
                                'diff': individual_profit
                            })

                        profit_moyen = total_ev - total_cost
                        roi = (profit_moyen / total_cost) * 100 if total_cost > 0 else 0
                        
                        if roi >= MIN_ROI:
                            st_tag = "[ST] " if is_st else ""
                            penalty_warn = f" (Incl. overpay FT: {buy_price-base_buy_price:+.2f})" if buy_price > base_buy_price else ""
                            
                            print(f"\n✨ COLLECTION: {coll['name']}")
                            print(f"👉 CONTRAT: 10x {st_tag}{inp['market_hash_name']} ({buy_cond})")
                            print(f"   Float requis: < {real_f:.4f} (Adj: {adj_target:.2f}){penalty_warn}")
                            print(f"   COÛT TOTAL: {total_cost:.2f} | EV: {total_ev:.2f} | PROFIT MOYEN: {profit_moyen:+.2f} | ROI: {roi:.1f}%")
                            print(f"   DROP TABLE (Valeur nette vs Coût contrat de {total_cost:.2f}):")
                            
                            for d in drop_table:
                                color_symbol = "🟢" if d['diff'] >= 0 else "🔴"
                                print(f"     {color_symbol} {d['name'][:25]:<25} ({d['cond']}): {d['val']:>8.2f} (Profit: {d['diff']:>+8.2f})")
                            print("-" * 60)

    conn.close()

if __name__ == "__main__":
    run_scanner()