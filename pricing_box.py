import json
import math
import os

# Standard CS2 Float Boundaries (Real Float)
LIMIT_FN = 0.07
LIMIT_MW = 0.15
LIMIT_FT = 0.38
LIMIT_WW = 0.45
# Psychological Barriers (Real Float)
BARRIER_BS_TRANSITION = 0.75

class PricingEngine:
    def __init__(self, model_params_path="data/model_params.json"):
        if not os.path.isabs(model_params_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.model_params_path = os.path.join(base_dir, model_params_path)
        else:
            self.model_params_path = model_params_path
        self._model_params = None

    @property
    def model_params(self):
        if self._model_params is None:
            self._load_params()
        return self._model_params

    def _load_params(self):
        try:
            if os.path.exists(self.model_params_path):
                with open(self.model_params_path, "r") as f:
                    self._model_params = json.load(f)
            else:
                self._model_params = {}
        except Exception:
            self._model_params = {}

    def predict_price(self, target_real_float, skin_min, skin_max, base_prices, rarity, is_st):
        """
        Rulebook-based pricing engine.
        Classification is based on target_real_float.
        Overpay is based on adjusted_float.
        """
        f = target_real_float
        adj = (f - skin_min) / (skin_max - skin_min) if (skin_max - skin_min) > 0 else 0
        adj = max(0.0, min(1.0, adj))

        # 1. Sanitization / Fallbacks
        bp = self._apply_fallbacks(base_prices)
        
        # WW Ignore logic
        ignore_ww = False
        if bp.get("WW") is not None and bp.get("FT") is not None:
            if bp["WW"] >= bp["FT"]:
                ignore_ww = True

        # --- THE RULEBOOK ---

        # RULE 0: Best Quality Exception (Lowest possible float for this specific skin)
        # If it's the absolute best version of the skin, we allow exponential overpay
        # even if it's not FN (e.g. AWP Asiimov 0.18).
        is_best_possible = (f <= skin_min + 0.0005)

        # RULE E: Zone Factory New (FN) [0.00 - 0.07] OR Best Quality
        if f < LIMIT_FN or is_best_possible:
            # We use FN price as base for exponential overpay if available, 
            # otherwise we use the best condition price available.
            price_base = bp["FN"] if f < LIMIT_FN else bp[self._get_cond(skin_min)]
            
            model_key = f"{rarity}_{int(is_st)}"
            params = self.model_params.get(model_key, {"alpha": 0, "k": 0})
            alpha = params.get("alpha", 0)
            k = params.get("k", 0)
            
            return price_base * (1 + alpha * math.exp(-k * adj))

        # RULE D: Zone MW [0.07 - 0.15]
        elif f < LIMIT_MW:
            # Linear transition to 90% of FN price at 0.0701
            # f=0.15 -> base_MW
            # f=0.07 -> Jump to FN happens elsewhere, here we approach 0.9 * FN
            return self._lerp(LIMIT_MW, LIMIT_FN, bp["MW"], 0.9 * bp["FN"], f)

        # RULE C: Zone FT [0.15 - 0.38]
        elif f < LIMIT_FT:
            if f >= 0.30:
                return bp["FT"]
            else:
                # Linear transition to 90% of MW price at 0.1501
                return self._lerp(0.30, LIMIT_MW, bp["FT"], 0.9 * bp["MW"], f)

        # RULE B: Zone Transition BS/WW to FT [0.38 - 0.75]
        elif f < BARRIER_BS_TRANSITION:
            if ignore_ww:
                return self._lerp(BARRIER_BS_TRANSITION, LIMIT_FT, bp["BS"], bp["FT"], f)
            else:
                if f >= LIMIT_WW:
                    return self._lerp(BARRIER_BS_TRANSITION, LIMIT_WW, bp["BS"], bp["WW"], f)
                else:
                    return self._lerp(LIMIT_WW, LIMIT_FT, bp["WW"], bp["FT"], f)

        # RULE A: Zone Battle-Scarred (BS) [0.75 - 1.0]
        else:
            return bp["BS"]

    def _get_cond(self, f):
        if f < LIMIT_FN: return "FN"
        if f < LIMIT_MW: return "MW"
        if f < LIMIT_FT: return "FT"
        if f < LIMIT_WW: return "WW"
        return "BS"

    def _apply_fallbacks(self, bp_input):
        bp = bp_input.copy()
        order = ["FN", "MW", "FT", "WW", "BS"]
        # Upward fill
        for i in range(len(order)-1, -1, -1):
            if bp.get(order[i]) is None:
                for j in range(i-1, -1, -1):
                    if bp.get(order[j]) is not None:
                        bp[order[i]] = bp[order[j]]
                        break
        # Downward fill
        for i in range(len(order)):
            if bp.get(order[i]) is None:
                for j in range(i+1, len(order)):
                    if bp.get(order[j]) is not None:
                        bp[order[i]] = bp[order[j]]
                        break
        return bp

    def _lerp(self, x1, x2, y1, y2, x):
        return y1 + (y2 - y1) * (x - x1) / (x2 - x1)

engine = PricingEngine()

def predict_price(target_real_float, skin_min, skin_max, base_prices, rarity, is_st):
    return engine.predict_price(target_real_float, skin_min, skin_max, base_prices, rarity, is_st)
