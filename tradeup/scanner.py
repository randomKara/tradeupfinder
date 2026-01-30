import json
import time
from .config import (
    RMB_TO_USD_RATE, FEE, MIN_ROI, MIN_INPUT_ADJ_FLOAT, 
    MIN_OUTPUT_PRICE, MAX_OUTPUT_PRICE, STD_FLOATS,
    REPORTS_DIR
)
from .utils import get_condition_code
from .database import get_db_connection

class TradeupScanner:
    def __init__(self):
        self.skins = {}
        self.prices_map = {} # (skin_id, is_st) -> data
        self.collections = {}

    def load_data(self):
        """Loads all necessary data from the database."""
        conn = get_db_connection()
        self.collections = {row['id']: row['name'] for row in conn.execute("SELECT id, name FROM collections")}
        
        cursor = conn.execute("SELECT * FROM skins")
        for row in cursor:
            self.skins[row['id']] = dict(row)
            
        cursor = conn.execute("SELECT * FROM prices")
        for row in cursor:
            sid, st, cond = row['skin_id'], row['is_stattrak'], row['condition']
            price = row['price'] * RMB_TO_USD_RATE
            pred = (row['predicted_price'] * RMB_TO_USD_RATE) if row['predicted_price'] else price
            
            key = (sid, st)
            if key not in self.prices_map:
                self.prices_map[key] = {
                    'prices': {}, 'pred_prices': {}, 
                    'irregular': {}, 'sell_nums': {}
                }
            
            self.prices_map[key]['prices'][cond] = price
            self.prices_map[key]['pred_prices'][cond] = pred
            self.prices_map[key]['irregular'][cond] = bool(row['irregular'])
            self.prices_map[key]['sell_nums'][cond] = row['sell_num']
        conn.close()
        print(f"Loaded {len(self.skins)} skins and price data.")

    def calculate_premium_price(self, real_f, base_price, skin_prices):
        """Calculates the price for low-float items based on better condition prices."""
        cond = get_condition_code(real_f)
        target_cond = None
        start_f, end_f = 0.0, 0.0
        
        if cond == "FT" and real_f < 0.38:
            target_cond, start_f, end_f = "MW", 0.38, 0.15
        elif cond == "MW" and real_f < 0.15:
            target_cond, start_f, end_f = "FN", 0.15, 0.07
        elif cond == "BS" and real_f < 0.6:
            target_cond, start_f, end_f = "WW", 0.6, 0.45

        if target_cond:
            target_price = skin_prices.get(target_cond)
            if target_price and target_price > base_price:
                factor = max(0, min(1, (start_f - real_f) / (start_f - end_f)))
                premium = (target_price - base_price) * (factor * 0.8) # 0.8 = FT_PENALTY_MAX_RATIO
                return base_price + premium
        return base_price

    def calculate_thresholds(self, outputs):
        """Determines critical Adjusted Float thresholds to hit target conditions."""
        thresholds = set()
        for skin in outputs:
            r_min, r_max = skin['min_float'], skin['max_float']
            r_range = r_max - r_min
            if r_range <= 0: continue
            
            for border in [0.07, 0.15, 0.38]:
                if r_min < border < r_max:
                    safe_adj = ((border - r_min) / r_range) - 0.0001
                    if 0 < safe_adj < 1:
                        thresholds.add(round(safe_adj, 5))
        return sorted(list(thresholds))

    def scan(self):
        """Main scanner logic."""
        targets, fillers_by_group = self._build_candidate_lists()
        results = []
        outputs_cache = {}

        def get_outputs(col_id, rank):
            k = (col_id, rank)
            if k not in outputs_cache:
                outputs_cache[k] = [s for s in self.skins.values() if s['collection_id'] == col_id and s['rarity_rank'] == rank + 1]
            return outputs_cache[k]

        print(f"Scanning {len(targets)} targets against cached fillers...")
        for target in targets:
            target_outputs = get_outputs(target['collection_id'], target['rarity'])
            if not target_outputs: continue
            
            thresholds = self.calculate_thresholds(target_outputs)
            for required_avg in thresholds:
                max_filler_adj = ((10 * required_avg) - target['adj_f']) / 9.0
                if max_filler_adj < 0: continue
                
                # Find best filler
                group_key = (target['rarity'], target['is_st'])
                fillers = fillers_by_group.get(group_key, [])
                
                for filler in fillers:
                    if filler['collection_id'] == target['collection_id']: continue
                    
                    needed_adj = min(max_filler_adj, 1.0)
                    if needed_adj < 0.001: continue
                    
                    required_real_f = filler['min_f'] + (needed_adj * (filler['max_f'] - filler['min_f']))
                    if get_condition_code(required_real_f) != filler['cond']: continue
                    
                    f_prices = self.prices_map[(filler['id'], filler['is_st'])]['prices']
                    final_filler_price = self.calculate_premium_price(required_real_f, filler['price'], f_prices)
                    
                    premium_val = final_filler_price - filler['price']
                    if needed_adj < MIN_INPUT_ADJ_FLOAT and premium_val <= 0.0001:
                        continue
                        
                    # Calculate Stats
                    filler_outputs = get_outputs(filler['collection_id'], filler['rarity'])
                    if not filler_outputs: continue
                    
                    res_obj = self._evaluate_mix(target, filler, required_avg, needed_adj, target_outputs, filler_outputs)
                    if res_obj:
                        results.append(res_obj)
                    break # Next threshold

        results.sort(key=lambda x: x['financials']['profit'], reverse=True)
        return results

    def _build_candidate_lists(self):
        targets = []
        fillers_by_group = {}
        
        for sid, skin in self.skins.items():
            rank, col_id = skin['rarity_rank'], skin['collection_id']
            if rank >= 6 or "Limited Edition" in self.collections.get(col_id, ""): 
                continue
            
            for is_st in [0, 1]:
                pkey = (sid, is_st)
                if pkey not in self.prices_map: continue
                
                for cond, price in self.prices_map[pkey]['prices'].items():
                    if price <= 0: continue
                    avg_f = STD_FLOATS.get(cond)
                    if not avg_f: continue
                    
                    avg_f = max(skin['min_float'], min(skin['max_float'], avg_f))
                    adj_f = (avg_f - skin['min_float']) / (skin['max_float'] - skin['min_float']) if (skin['max_float']-skin['min_float']) > 0 else 0
                    
                    item = {
                        'id': sid, 'name': skin['market_hash_name'], 'collection_id': col_id,
                        'rarity': rank, 'is_st': is_st, 'cond': cond, 'price': price,
                        'min_f': skin['min_float'], 'max_f': skin['max_float'],
                        'real_f': avg_f, 'adj_f': adj_f, 'is_irregular': self.prices_map[pkey]['irregular'][cond]
                    }
                    targets.append(item)
                    
                    gk = (rank, is_st)
                    if gk not in fillers_by_group: fillers_by_group[gk] = []
                    fillers_by_group[gk].append(item)

        for gk in fillers_by_group:
            fillers_by_group[gk].sort(key=lambda x: x['price'])
            fillers_by_group[gk] = fillers_by_group[gk][:50]
            
        return targets, fillers_by_group

    def _evaluate_mix(self, target, filler, required_avg, filler_needed_adj, t_outs, f_outs):
        cost = target['price'] + (9 * filler['price'])
        mix_avg_adj = (target['adj_f'] + 9 * filler_needed_adj) / 10.0
        
        ev = 0
        outcomes = []
        
        # 10% target, 90% filler
        p_t = 0.1 / len(t_outs)
        p_f = 0.9 / len(f_outs)
        
        for out_list, prob, source in [(t_outs, p_t, 'target'), (f_outs, p_f, 'filler')]:
            for o in out_list:
                res_f = o['min_float'] + mix_avg_adj * (o['max_float'] - o['min_float'])
                res_c = get_condition_code(res_f)
                
                st_status = target['is_st'] if source == 'target' else filler['is_st']
                pkey = (o['id'], st_status)
                
                if pkey in self.prices_map:
                    is_irreg = self.prices_map[pkey]['irregular'].get(res_c, False)
                    p_val = self.prices_map[pkey]['pred_prices'].get(res_c, 0) if is_irreg else self.prices_map[pkey]['prices'].get(res_c, 0)
                else:
                    p_val, is_irreg = 0, False
                
                net_val = p_val * FEE
                ev += net_val * prob
                outcomes.append({
                    "name": o['market_hash_name'], "condition": res_c,
                    "probability": prob * 100, "value_net": net_val,
                    "profit": net_val - cost, "source": source, "was_irregular": is_irreg
                })
        
        profit = ev - cost
        roi = (profit / cost * 100) if cost > 0 else 0
        
        if roi >= MIN_ROI and profit > 0.5:
            return {
                "type": "MIX_1_9", "is_stattrak": bool(target['is_st']),
                "target_collection": self.collections[target['collection_id']],
                "filler_collection": self.collections[filler['collection_id']],
                "inputs": {
                    "target": target, "filler": filler
                },
                "financials": {"total_cost": cost, "expected_value": ev, "roi": roi, "profit": profit},
                "outcomes": sorted(outcomes, key=lambda x: x['value_net'], reverse=True)
            }
        return None
