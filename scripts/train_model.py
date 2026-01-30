import json
import sqlite3
import os
import numpy as np
from scipy.optimize import curve_fit
import sys

# Add root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradeup.config import DB_PATH, DATA_DIR

DETAILED_JSON_PATH = os.path.join(DATA_DIR, "detailled_float.json")
MODEL_PARAMS_PATH = os.path.join(DATA_DIR, "model_params.json")

def model_func(adj_f, alpha, k):
    """Exponential decay model for price ratio vs adjusted float."""
    return 1 + alpha * np.exp(-k * adj_f)

def train():
    if not os.path.exists(DETAILED_JSON_PATH):
        print(f"Error: {DETAILED_JSON_PATH} not found.")
        return

    # 1. Load Data
    with open(DETAILED_JSON_PATH, "r") as f:
        json_data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get skin metadata linked by goods_id
    cursor.execute('''
        SELECT p.goods_id, s.rarity_rank, p.is_stattrak, s.min_float, s.max_float
        FROM prices p
        JOIN skins s ON p.skin_id = s.id
    ''')
    skin_meta = {row['goods_id']: dict(row) for row in cursor.fetchall()}
    conn.close()

    training_groups = {} # (rarity, is_st) -> {'x': [], 'y': []}

    # 2. Extract Points
    for item in json_data['info']:
        gid = item['goods_id']
        if gid not in skin_meta:
            continue
        
        meta = skin_meta[gid]
        rarity = meta['rarity_rank']
        is_st = meta['is_stattrak']
        min_f, max_f = meta['min_float'], meta['max_float']
        f_range = max_f - min_f
        
        if f_range <= 0: continue

        sales = item['sales']
        # Filter buckets (those with min_float)
        buckets = [s for s in sales if 'min_float' in s]
        if not buckets: continue

        # Find base price (0.04 - 0.07 range or cheapest)
        base_price = None
        for b in buckets:
            if b.get('min_float') == "0.04":
                base_price = float(b['min_price'])
                break
        if not base_price:
            base_price = min(float(b['min_price']) for b in buckets)

        key = (rarity, is_st)
        if key not in training_groups:
            training_groups[key] = {'x': [], 'y': []}

        for b in buckets:
            price = float(b['min_price'])
            b_min = float(b['min_float'])
            
            # Adjusted Float
            adj_f = (b_min - min_f) / f_range
            adj_f = max(0, min(1, adj_f)) # Clamp
            
            ratio = price / base_price
            
            training_groups[key]['x'].append(adj_f)
            training_groups[key]['y'].append(ratio)

    # 3. Fit Curves
    model_params = {}

    for (rarity, is_st), data in training_groups.items():
        x = np.array(data['x'])
        y = np.array(data['y'])

        if len(x) < 3:
            print(f"Skipping (Rarity {rarity}, ST {is_st}): Not enough data ({len(x)} points)")
            continue

        try:
            # Initial guess: alpha=2.0 (item worth 3x at 0 float), k=10.0 (fast decay)
            popt, _ = curve_fit(model_func, x, y, p0=[2.0, 10.0], bounds=(0, [100.0, 100.0]))
            
            group_name = f"{rarity}_{is_st}"
            model_params[group_name] = {
                "alpha": round(float(popt[0]), 4),
                "k": round(float(popt[1]), 4)
            }
            print(f"Success: (Rarity {rarity}, ST {is_st}) -> alpha={model_params[group_name]['alpha']}, k={model_params[group_name]['k']}")
        except Exception as e:
            print(f"Failed to fit (Rarity {rarity}, ST {is_st}): {e}")

    # 4. Save
    with open(MODEL_PARAMS_PATH, "w") as f:
        json.dump(model_params, f, indent=4)
    
    print(f"\nTraining complete. Saved params to {MODEL_PARAMS_PATH}")

if __name__ == "__main__":
    train()
