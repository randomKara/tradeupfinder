import argparse
import sys
from scripts.update_db import update_prices
from scripts.scan_mixes import run_scan

def main():
    parser = argparse.ArgumentParser(description="CS2 TradeUp Finder CLI")
    parser.add_argument("command", choices=["update", "scan"], help="Command to run")
    
    args = parser.parse_args()
    
    if args.command == "update":
        update_prices()
    elif args.command == "scan":
        run_scan()

if __name__ == "__main__":
    main()
