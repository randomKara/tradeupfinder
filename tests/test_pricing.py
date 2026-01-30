import time
from pricing_box import predict_price

def test_segments():
    test_bp = {"FN": 100.0, "MW": 50.0, "FT": 20.0, "WW": 15.0, "BS": 10.0}
    skin_min = 0.0
    skin_max = 1.0
    rarity = "2"
    is_st = 0

    print("--- Testing Segments ---")
    
    # 1. BS Zone [0.75 - 1.0]
    p_bs = predict_price(0.8, skin_min, skin_max, test_bp, rarity, is_st)
    print(f"BS (0.8): {p_bs} (Expected: 10.0)")
    assert p_bs == 10.0

    # 2. Transition BS to WW [0.45 - 0.75]
    p_trans1 = predict_price(0.6, skin_min, skin_max, test_bp, rarity, is_st)
    # Lerp (0.75, 0.45, 10, 15, 0.6)
    expected_trans1 = 10 + (15 - 10) * (0.6 - 0.75) / (0.45 - 0.75)
    print(f"BS-WW (0.6): {p_trans1} (Expected: {expected_trans1})")
    assert abs(p_trans1 - expected_trans1) < 1e-6

    # 3. Transition WW to FT [0.38 - 0.45]
    p_trans2 = predict_price(0.4, skin_min, skin_max, test_bp, rarity, is_st)
    # Lerp (0.45, 0.38, 15, 20, 0.4)
    expected_trans2 = 15 + (20 - 15) * (0.4 - 0.45) / (0.38 - 0.45)
    print(f"WW-FT (0.4): {p_trans2} (Expected: {expected_trans2})")
    assert abs(p_trans2 - expected_trans2) < 1e-6

    # 4. FT Plate [0.30 - 0.38]
    p_ft_plate = predict_price(0.35, skin_min, skin_max, test_bp, rarity, is_st)
    print(f"FT Plate (0.35): {p_ft_plate} (Expected: 20.0)")
    assert p_ft_plate == 20.0

    # 5. FT to MW Barrier (0.15, 0.30)
    p_ft_mw = predict_price(0.2, skin_min, skin_max, test_bp, rarity, is_st)
    # Lerp (0.30, 0.15, 20, 0.9*50=45, 0.2)
    expected_ft_mw = 20 + (45 - 20) * (0.2 - 0.30) / (0.15 - 0.30)
    print(f"FT-MW Lerp (0.2): {p_ft_mw} (Expected: {expected_ft_mw})")
    assert abs(p_ft_mw - expected_ft_mw) < 1e-6

    # 6. MW Jump at 0.15
    p_mw_jump = predict_price(0.15, skin_min, skin_max, test_bp, rarity, is_st)
    print(f"MW Jump (0.15): {p_mw_jump} (Expected: 50.0)")
    assert p_mw_jump == 50.0

    # 7. MW to FN Barrier (0.07, 0.15)
    p_mw_fn = predict_price(0.1, skin_min, skin_max, test_bp, rarity, is_st)
    # Lerp (0.15, 0.07, 50, 0.9*100=90, 0.1)
    expected_mw_fn = 50 + (90 - 50) * (0.1 - 0.15) / (0.07 - 0.15)
    print(f"MW-FN Lerp (0.1): {p_mw_fn} (Expected: {expected_mw_fn})")
    assert abs(p_mw_fn - expected_mw_fn) < 1e-6

    # 8. FN Jump at 0.07
    p_fn_jump = predict_price(0.07, skin_min, skin_max, test_bp, rarity, is_st)
    print(f"FN Jump (0.07): {p_fn_jump} (Expected: 100.0)")
    assert p_fn_jump == 100.0

    # 9. FN Exponential [0.00 - 0.07]
    p_fn_exp = predict_price(0.01, skin_min, skin_max, test_bp, "2", 0)
    print(f"FN Exp (0.01): {p_fn_exp} (Expected: > 100.0, using model params for 2_0)")
    assert p_fn_exp > 100.0

def test_ww_ignore():
    test_bp = {"FN": 100, "MW": 50, "FT": 20, "WW": 22, "BS": 10} # WW >= FT
    skin_min, skin_max = 0.0, 1.0
    
    print("\n--- Testing WW Ignore ---")
    p_trans = predict_price(0.5, skin_min, skin_max, test_bp, "1", 0)
    # Lerp (0.75, 0.38, 10, 20, 0.5) because WW is ignored
    expected = 10 + (20 - 10) * (0.5 - 0.75) / (0.38 - 0.75)
    print(f"WW Ignored Lerp (0.5): {p_trans} (Expected: {expected})")
    assert abs(p_trans - expected) < 1e-6

def test_fallbacks():
    test_bp = {"FN": 100, "MW": None, "FT": 20, "WW": None, "BS": None}
    print("\n--- Testing Fallbacks ---")
    
    # BS should fallback to FT (since WW is also None)
    # Actually BS -> WW -> FT
    p_bs = predict_price(0.9, 0, 1, test_bp, "1", 0)
    print(f"BS Fallback (0.9): {p_bs} (Expected: 20.0 - from FT)")
    assert p_bs == 20.0
    
    # MW should fallback to FN
    p_mw = predict_price(0.15, 0, 1, test_bp, "1", 0)
    print(f"MW Fallback (0.15): {p_mw} (Expected: 100.0 - from FN)")
    assert p_mw == 100.0

def benchmark():
    test_bp = {"FN": 100, "MW": 50, "FT": 20, "WW": 15, "BS": 10}
    n = 100000
    start = time.perf_counter()
    for i in range(n):
        predict_price(0.01, 0, 1, test_bp, "2", 0)
    end = time.perf_counter()
    avg_us = (end - start) / n * 1_000_000
    print(f"\n--- Benchmark ---")
    print(f"Average time per prediction: {avg_us:.2f} microseconds")
    assert avg_us < 100 # Should be well under 100us, usually around 1-5us

if __name__ == "__main__":
    test_segments()
    test_ww_ignore()
    test_fallbacks()
    benchmark()
    print("\nAll tests passed!")
