import os

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

DB_PATH = os.path.join(DATA_DIR, "cs2_skins.db")
OVERRIDES_PATH = os.path.join(DATA_DIR, "manual_overrides.json")
PRICE_JSON_PATH = os.path.join(DATA_DIR, "price.json")
MODEL_PARAMS_PATH = os.path.join(DATA_DIR, "model_params.json")

# --- MARKET RATES ---
RMB_TO_USD_RATE = 0.1439
FEE = 0.95  # 5% fee on Buff buy+sell

# --- SCANNER CONFIG ---
MIN_ROI = 10.0
MIN_INPUT_ADJ_FLOAT = 0.05
MIN_OUTPUT_PRICE = 0.5
MAX_OUTPUT_PRICE = 2000.0
ENABLE_STATTRAK = True

# --- SANITIZER CONFIG ---
OUTLIER_SIGMA = 2.5
SCARCITY_EXPONENT = 1.0
MIN_SAMPLES_FOR_STATS = 3
ANOMALY_THRESHOLD = 5.0

# --- GLOBAL CONSTANTS ---
CONDITION_BOUNDS = {
    'FN': (0.0, 0.07),
    'MW': (0.07, 0.15),
    'FT': (0.15, 0.38),
    'WW': (0.38, 0.45),
    'BS': (0.45, 1.0)
}

CONDITION_MAP_BUFF = {
    "Factory New": "FN",
    "Minimal Wear": "MW",
    "Field-Tested": "FT",
    "Well-Worn": "WW",
    "Battle-Scarred": "BS"
}

STD_FLOATS = {
    "FN": 0.035,
    "MW": 0.10,
    "FT": 0.25,
    "WW": 0.42,
    "BS": 0.60
}
