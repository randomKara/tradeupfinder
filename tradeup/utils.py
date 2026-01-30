import re
from .config import CONDITION_BOUNDS, CONDITION_MAP_BUFF

def get_condition_code(f):
    """Returns the quality code for a given float value."""
    if f < 0.07: return "FN"
    if f < 0.15: return "MW"
    if f < 0.38: return "FT"
    if f < 0.45: return "WW"
    return "BS"

def parse_market_name(full_name):
    """
    Parses a Buff market name into (base_name, condition, is_stattrak).
    """
    if "Souvenir" in full_name:
        return None, None, None

    is_stattrak = 1 if "StatTrak™" in full_name else 0
    clean_name = full_name.replace("StatTrak™ ", "")

    # Pattern to match condition at the end of the string
    pattern = r'\s\((Factory New|Minimal Wear|Field-Tested|Well-Worn|Battle-Scarred)\)$'
    match = re.search(pattern, clean_name)
    
    if not match:
        return None, None, None
        
    buff_condition = match.group(1)
    skin_base_name = clean_name[:match.start()].strip()
    
    # Handle Dopplers & Phases
    phase_pattern = r'\s\((Phase \d|Emerald|Ruby|Sapphire|Black Pearl)\)$'
    skin_base_name = re.sub(phase_pattern, "", skin_base_name).strip()

    return skin_base_name, CONDITION_MAP_BUFF.get(buff_condition), is_stattrak

def calculate_adjusted_float_range(min_f, max_f, condition):
    """Calculates the adjusted float range and bounds for a specific skin condition."""
    cond_min, cond_max = CONDITION_BOUNDS[condition]
    actual_min = max(min_f, cond_min)
    actual_max = min(max_f, cond_max)
    
    adj_range = (actual_max - actual_min) / (max_f - min_f) if (max_f - min_f) > 0 else 0
    return adj_range, actual_min, actual_max
