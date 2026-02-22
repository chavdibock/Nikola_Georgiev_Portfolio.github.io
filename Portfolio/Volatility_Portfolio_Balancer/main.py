import sys
import time
import pandas as pd

INPUT_FILE = "filtered_stocks.csv"
OUTPUT_FILE = "enriched_stocks.csv"
SLEEP_BETWEEN_REQUESTS = 0.0  # seconds (set to 1.0 if hitting rate limits)


def find_symbol_column(df: pd.DataFrame) -> str:
    candidates = ["symbol", "Symbol", "ticker", "Ticker", "SYMBOL", "TICKER"]
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(
        f"Could not find a symbol/ticker column in {list(df.columns)}. "
        "Expected one of: symbol, Symbol, ticker, Ticker, SYMBOL, TICKER"
    )


def get_metrics_for_symbol(sym: str, yf_module):
    """Fetch P/E, P/B, PEG, and P/Cashflow ratios from Yahoo Finance."""
    try:
        t = yf_module.Ticker(sym)
        try:
            info = t.get_info()

        except Exception as e:
            print("Error", e)
            info = t.info or {}

        turnover_ratio = info.get("volume") / info.get("floatShares")
        if turnover_ratio < 0.005:
            return None

        price = info.get("ask")
        cash = info.get("operatingCashflow")
        book_value = info.get("bookValue")
        earnings = info.get("grossProfits")

        pe = price / earnings
        pb = price / book_value
        pcash = price / cash

        metrics = dict(p_e=pe, p_b=pb, p_cash=pcash)

        # All four must exist and be finite
        for k, v in metrics.items():
            if v is None:
                return None
            try:
                fv = float(v)
                if fv != fv:  # NaN check
                    return None
                metrics[k] = fv
            except Exception as e:
                print("Error", e)
                return None

        return metrics
    except Exception as e:
        print("Error", e)
        return None


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("Error: yfinance not installed. Run: pip install yfinance pandas", file=sys.stderr)
        sys.exit(1)

    print(f"Reading input file: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE)
    sym_col = find_symbol_column(df)

    records = []
    kept, dropped = 0, 0

    for _, row in df.iterrows():
        sym = str(row[sym_col]).strip()
        if not sym or sym.lower() in ("nan", "none"):
            dropped += 1
            continue

        metrics = get_metrics_for_symbol(sym, yf)
        if metrics is None:
            print(f"Skipping {sym}: missing data")
            dropped += 1
        else:
            new_row = row.to_dict()
            new_row.update(metrics)
            records.append(new_row)
            kept += 1
            print(f"Fetched {sym}: OK")

        if SLEEP_BETWEEN_REQUESTS > 0:
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    if not records:
        print("No symbols with complete data found. Exiting.")
        sys.exit(2)

    out_df = pd.DataFrame.from_records(records)
    out_df.to_csv(OUTPUT_FILE, index=False)

    print(f" saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
