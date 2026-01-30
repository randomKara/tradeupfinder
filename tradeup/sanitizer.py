import json
import math
import os
import sqlite3
import numpy as np
from scipy.optimize import curve_fit
from collections import defaultdict
from .config import (
    DB_PATH, OVERRIDES_PATH, RMB_TO_USD_RATE, MODEL_PARAMS_PATH,
    OUTLIER_SIGMA, SCARCITY_EXPONENT, MIN_SAMPLES_FOR_STATS, ANOMALY_THRESHOLD,
    CONDITION_BOUNDS
)
from .utils import calculate_adjusted_float_range

class PriceSanitizer:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.skins = {}  # skin_id -> {name, collection_id, rarity, min_float, max_float}
        self.prices = {}  # (skin_id, condition, is_st) -> price
        self.collection_stats = {}  # (collection_id, rarity, is_st) -> stats
        self.global_stats = {}  # rarity -> regression params
        self.model_params = {}  # rarity_st -> {alpha, k}
        self.manual_overrides = {} # (skin_name, cond, is_st) -> price
        self.load_manual_overrides()
        self.load_model_params()

    def load_manual_overrides(self):
        """Load manual price overrides from JSON if exists"""
        try:
            if os.path.exists(OVERRIDES_PATH):
                with open(OVERRIDES_PATH, "r") as f:
                    data = json.load(f)
                    for item in data:
                        key = (item['skin'], item['condition'], bool(item['is_stattrak']))
                        self.manual_overrides[key] = item['price']
                print(f"Loaded {len(self.manual_overrides)} manual price overrides.")
        except Exception as e:
            print(f"Warning: Failed to load manual overrides: {e}")

    def load_model_params(self):
        """Load trained exponential model parameters"""
        try:
            if os.path.exists(MODEL_PARAMS_PATH):
                with open(MODEL_PARAMS_PATH, "r") as f:
                    self.model_params = json.load(f)
                print(f"Loaded {len(self.model_params)} rarity model parameters.")
        except Exception as e:
            print(f"Warning: Failed to load model_params.json: {e}")
        
    def load_data(self):
        """Load all data from SQLite into RAM"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Load skins
        cursor.execute("SELECT * FROM skins")
        for row in cursor.fetchall():
            self.skins[row['id']] = dict(row)
        
        # Load prices
        cursor.execute("SELECT * FROM prices")
        for row in cursor.fetchall():
            skin_id = row['skin_id']
            if skin_id in self.skins:
                self.prices[(skin_id, row['condition'], row['is_stattrak'])] = row['price'] * RMB_TO_USD_RATE
        
        conn.close()

    def build_collection_stats(self):
        """Method 1: Builds statistics based on collection ratios"""
        groups = defaultdict(list)
        for (sid, cond, is_st), price in self.prices.items():
            skin = self.skins[sid]
            groups[(skin['collection_id'], skin['rarity_rank'], is_st)].append(price)
            
        for key, prices in groups.items():
            if len(prices) >= MIN_SAMPLES_FOR_STATS:
                self.collection_stats[key] = {
                    'median': np.median(prices),
                    'std': np.std(prices)
                }

    def build_global_regression(self):
        """Method 2: Builds rarity-based price curves"""
        rarity_curves = defaultdict(lambda: {'points': [], 'base_prices': {}})
        
        for (sid, cond, is_st), price in self.prices.items():
            skin = self.skins[sid]
            adj, _, _ = calculate_adjusted_float_range(skin['min_float'], skin['max_float'], cond)
            if adj > 0:
                rarity_curves[(sid, is_st)]['points'].append((cond, adj, price))
        
        self.global_stats = {}
        for (sid, is_st), data in rarity_curves.items():
            points = data['points']
            if not points: continue
            
            # Use cheapest valid condition as base
            points.sort(key=lambda x: x[2])
            base_cond, base_adj, base_price = points[0]
            
            if base_price > 0:
                self.global_stats[(sid, is_st)] = {
                    'base_cond': base_cond,
                    'base_adj_range': base_adj,
                    'base_price': base_price,
                    'scaling_factor': 1.0 # Simple linear model for now
                }

    def get_predicted_price(self, skin_id, condition, is_st):
        """Combined prediction with manual override check"""
        skin = self.skins.get(skin_id)
        if skin:
            m_key = (skin['market_hash_name'], condition, bool(is_st))
            if m_key in self.manual_overrides:
                return self.manual_overrides[m_key]

        # Method 1 logic
        p1 = None
        key = (skin['collection_id'], skin['rarity_rank'], is_st)
        if key in self.collection_stats:
            p1 = self.collection_stats[key]['median']

        # Method 2 logic : Exponential Model or Linear Scarcity
        p2 = None
        ckey = (skin_id, is_st)
        m_key = f"{skin['rarity_rank']}_{is_st}"
        
        if ckey in self.global_stats:
            curve = self.global_stats[ckey]
            target_adj, _, _ = calculate_adjusted_float_range(skin['min_float'], skin['max_float'], condition)
            
            if m_key in self.model_params and target_adj > 0:
                # Use trained exponential model
                m = self.model_params[m_key]
                alpha, k = m['alpha'], m['k']
                
                # Predict factor relative to base condition
                # Base adj for the best condition found in stats
                base_adj, _, _ = calculate_adjusted_float_range(skin['min_float'], skin['max_float'], curve['base_cond'])
                
                # Price(adj) = BasePrice * (1 + alpha * exp(-k * adj)) / (1 + alpha * exp(-k * base_adj))
                f_target = 1 + alpha * math.exp(-k * target_adj)
                f_base = 1 + alpha * math.exp(-k * base_adj)
                
                p2 = curve['base_price'] * (f_target / f_base)
            elif target_adj > 0:
                # Fallback to simple power law scarcity if no model params for this rarity
                if condition == curve['base_cond']:
                    p2 = curve['base_price']
                else:
                    p2 = curve['base_price'] * (curve['base_adj_range'] / target_adj) ** SCARCITY_EXPONENT
        
        # Combined weighting
        if p1 and p2:
            return 0.6 * p1 + 0.4 * p2
        return p1 or p2

    def detect_anomalies(self):
        """Logic for identifying price manipulations or errors."""
        anomalies = []
        for (skin_id, condition, is_st), actual_price in self.prices.items():
            predicted = self.get_predicted_price(skin_id, condition, is_st)
            if not predicted: continue
            
            # --- USER RULE: 1.5x better quality flag ---
            is_manipulated = False
            cond_order = ['BS', 'WW', 'FT', 'MW', 'FN']
            idx = cond_order.index(condition)
            for better_idx in range(idx + 1, len(cond_order)):
                better_p = self.prices.get((skin_id, cond_order[better_idx], is_st))
                if better_p and actual_price > 1.5 * better_p:
                    is_manipulated = True
                    break

            ratio = actual_price / predicted
            if ratio > ANOMALY_THRESHOLD or is_manipulated:
                anomalies.append({
                    "skin": self.skins[skin_id]['market_hash_name'],
                    "condition": condition,
                    "is_stattrak": bool(is_st),
                    "actual": round(actual_price, 2),
                    "predicted": round(predicted, 2),
                    "ratio": round(ratio, 2),
                    "reason": "MANIPULATION"
                })
        return anomalies
