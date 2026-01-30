import sqlite3

# --- CONFIGURATION ---
DB_NAME = "cs2_skins.db"
RMB_TO_USD_RATE = 0.1439
STEAM_FEE = 0.975          
MIN_ROI = 10.0            
MIN_INPUT_ADJ_FLOAT = 0.20 
MIN_OUTPUT_PRICE = 5.0     
MAX_OUTPUT_PRICE = 250.0   

# --- RÉGLAGES AVANCÉS ---
ENABLE_STATTRAK = True    # Changez en True pour inclure les StatTrak
FT_PENALTY_MAX_RATIO = 0.8 # À 0.151, on ajoute 80% de la diff FT/MW

def get_condition_code(f):
    if f < 0.07: return "FN"
    if f < 0.15: return "MW"
    if f < 0.38: return "FT"
    if f < 0.45: return "WW"
    return "BS"

def calculate_premium_price(real_f, base_price, skin_prices):
    """
    Simule l'overpay pour les low floats en FT, MW et BS.
    L'overpay ne commence qu'après une certaine deadzone (20% par défaut).
    """
    cond = get_condition_code(real_f)
    
    target_cond = None
    start_f, end_f = 0.0, 0.0
    deadzone = 0.20

    if cond == "FT" and real_f < 0.38:
        target_cond = "MW"
        start_f, end_f = 0.38, 0.15
    elif cond == "MW" and real_f < 0.15:
        target_cond = "FN"
        start_f, end_f = 0.15, 0.07
    elif cond == "BS" and real_f < 0.6:
        # Pour le BS, on commence l'overpay directement à 0.6 vers le prix WW
        target_cond = "WW"
        start_f, end_f = 0.6, 0.45
        deadzone = 0.0 # Seuil personnalisé à 0.6
    
    if target_cond:
        target_price = skin_prices.get(target_cond)
        if target_price and target_price > base_price:
            # Progression: 0.0 (Worst float) -> 1.0 (Best float for condition)
            factor = (start_f - real_f) / (start_f - end_f)
            factor = max(0, min(1, factor))

            # Application de la deadzone
            if factor <= deadzone:
                factor = 0
            else:
                # Rescale pour que l'augmentation soit progressive après la deadzone
                factor = (factor - deadzone) / (1.0 - deadzone)
            
            premium = (target_price - base_price) * (factor * FT_PENALTY_MAX_RATIO)
            return base_price + premium
            
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
    
    results = []

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

                # Conversion des prix output (max_price) en USD pour le filtrage
                for out in outputs:
                    if out['max_price'] is not None:
                        out['max_price'] *= RMB_TO_USD_RATE

                magic_floats = calculate_thresholds(outputs)
                if magic_floats is None: continue 

                # Prix
                cursor.execute("SELECT skin_id, condition, price FROM prices WHERE is_stattrak = ?", (is_st,))
                all_prices = {}
                for row in cursor.fetchall():
                    sid = row['skin_id']
                    if sid not in all_prices: all_prices[sid] = {}
                    # Conversion directe en USD lors du chargement
                    all_prices[sid][row['condition']] = row['price'] * RMB_TO_USD_RATE
                
                # Correction des prix WW irréalistes
                for sid in all_prices:
                    p = all_prices[sid]
                    if "WW" in p and "BS" in p:
                        # Si le prix WW est > 1.5x le prix BS, on le plafonne à 1.2x
                        if p["WW"] > p["BS"] * 1.5:
                            p["WW"] = p["BS"] * 1.2

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
                            results.append({
                                'coll_name': coll['name'],
                                'is_st': is_st,
                                'inp_name': inp['market_hash_name'],
                                'buy_cond': buy_cond,
                                'real_f': real_f,
                                'adj_target': adj_target,
                                'buy_price': buy_price,
                                'base_buy_price': base_buy_price,
                                'total_cost': total_cost,
                                'total_ev': total_ev,
                                'profit_moyen': profit_moyen,
                                'roi': roi,
                                'drop_table': drop_table
                            })

    # Tri par profit moyen décroissant
    results.sort(key=lambda x: x['profit_moyen'], reverse=True)

    for res in results:
        st_tag = "[ST] " if res['is_st'] else ""
        penalty_warn = f" (Incl. overpay FT: {res['buy_price']-res['base_buy_price']:+.2f})" if res['buy_price'] > res['base_buy_price'] else ""
        
        print(f"\n✨ COLLECTION: {res['coll_name']}")
        print(f"👉 CONTRAT: 10x {st_tag}{res['inp_name']} ({res['buy_cond']})")
        print(f"   Float requis: < {res['real_f']:.4f} (Adj: {res['adj_target']:.2f}){penalty_warn}")
        print(f"   COÛT TOTAL: {res['total_cost']:.2f} | EV: {res['total_ev']:.2f} | PROFIT MOYEN: {res['profit_moyen']:+.2f} | ROI: {res['roi']:.1f}%")
        print(f"   DROP TABLE (Valeur nette vs Coût contrat de {res['total_cost']:.2f}):")
        
        for d in res['drop_table']:
            color_symbol = "🟢" if d['diff'] >= 0 else "🔴"
            print(f"     {color_symbol} {d['name'][:25]:<25} ({d['cond']}): {d['val']:>8.2f} (Profit: {d['diff']:>+8.2f})")
        print("-" * 60)

    conn.close()

if __name__ == "__main__":
    run_scanner()