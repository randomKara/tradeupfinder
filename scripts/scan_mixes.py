import sys
import os
import json

# Add root folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradeup.scanner import TradeupScanner
from tradeup.config import REPORTS_DIR

def run_scan():
    scanner = TradeupScanner()
    scanner.load_data()
    results = scanner.scan()
    
    print(f"\nFound {len(results)} profitable opportunities.")
    
    output_path = os.path.join(REPORTS_DIR, "mix_results.json")
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"Results saved to {output_path}")
    
    if results:
        print("\nTop 3 results:")
        for i in range(min(3, len(results))):
            r = results[i]
            print(f"{i+1}. {r['inputs']['target']['name']} -> ROI: {r['financials']['roi']:.1f}% | Profit: ${r['financials']['profit']:.2f}")

if __name__ == "__main__":
    run_scan()
