import requests
import time
import json
from datetime import datetime

BINANCE_API_URL = "https://api.binance.com/api/v3/exchangeInfo"
CHECK_INTERVAL = 60  # seconds


def fetch_symbols():
    try:
        response = requests.get(BINANCE_API_URL)
        response.raise_for_status()
        data = response.json()
        symbols = [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING']
        return set(symbols)
    except Exception as e:
        print(f"[{datetime.now()}] Error fetching symbols: {e}")
        return set()


def load_known_symbols(filename="known_symbols.json"):
    try:
        with open(filename, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_known_symbols(symbols, filename="known_symbols.json"):
    with open(filename, "w") as f:
        json.dump(sorted(symbols), f)


def main():
    print("📡 Starting Binance new coin monitor...")
    known_symbols = load_known_symbols()

    while True:
        current_symbols = fetch_symbols()
        new_symbols = current_symbols - known_symbols

        if new_symbols:
            print(f"\n🆕 [{datetime.now()}] New listings detected:")
            for symbol in sorted(new_symbols):
                print(f" - {symbol}")
            known_symbols.update(new_symbols)
            save_known_symbols(known_symbols)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
