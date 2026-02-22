import numpy as np
import pandas as pd
import yfinance as yf

TICKERS = ["AAPL", "GOOGL", "AVGO", "NVDA", "PLTR", "AMZN",  "MFST", "TSLA", "ORCL", "CELC", "MU", "AMD", "SPY"]
START_DATE = "2025-10-17"
END_DATE = "2025-11-27"
CONSTANT_RF_ANNUAL = 0.03611
USE_MARKET_RF = False
MARKET_RF_TICKER = "^IRX"
OUTPUT_FILE = "historical_returns.xlsx"

def get_daily_risk_free_series(start, end):
    if not USE_MARKET_RF:
        rf_daily_val = CONSTANT_RF_ANNUAL / 252.0
        dates = pd.date_range(start=start, end=end, freq="B")
        return pd.Series(rf_daily_val, index=dates, name="rf_daily")

    rf_data = yf.download(MARKET_RF_TICKER, start=start, end=end, progress=False, auto_adjust=False)

    if rf_data.empty:
        raise ValueError("Risk-free data download failed or empty.")

    if "Adj Close" in rf_data.columns:
        rf_yield_pct = rf_data["Adj Close"]
    else:
        rf_yield_pct = rf_data["Close"]

    rf_yield_decimal = rf_yield_pct / 100.0
    rf_daily = rf_yield_decimal / 252.0

    if isinstance(rf_daily, pd.DataFrame):
        rf_daily = rf_daily.iloc[:, 0]

    rf_daily.name = "rf_daily"
    return rf_daily

def main():
    rf_series = get_daily_risk_free_series(START_DATE, END_DATE)

    with pd.ExcelWriter(OUTPUT_FILE, engine="xlsxwriter") as writer:
        for ticker in TICKERS:
            print(f"Processing {ticker}...")

            data = yf.download(ticker, start=START_DATE, end=END_DATE, progress=False, auto_adjust=False)

            if data.empty:
                print(f"No data for {ticker}. Skipping.")
                continue

            if "Adj Close" in data.columns:
                price_col = "Adj Close"
            else:
                price_col = "Close"

            prices = data[price_col].dropna()
            if isinstance(prices, pd.DataFrame):
                prices = prices.iloc[:, 0]
            prices.name = "Price"

            log_returns = np.log(prices / prices.shift(1))
            log_returns.name = "Log_Return"

            rf_aligned = rf_series.reindex(log_returns.index).ffill()

            if rf_aligned.isna().all():
                rf_aligned = pd.Series(0.0, index=log_returns.index, name="RF_Daily")
            else:
                first_non_na = rf_aligned.dropna().iloc[0]
                rf_aligned = rf_aligned.fillna(first_non_na)

            if isinstance(rf_aligned, pd.DataFrame):
                rf_aligned = rf_aligned.iloc[:, 0]
            rf_aligned.name = "RF_Daily"

            excess_returns = log_returns - rf_aligned
            excess_returns.name = "Excess_Return"

            df = pd.DataFrame({
                "Price": prices,
                "Log_Return": log_returns,
                "RF_Daily": rf_aligned,
                "Excess_Return": excess_returns
            })

            df = df.dropna(subset=["Log_Return"])

            if df.empty:
                print(f"No valid return data for {ticker}. Skipping.")
                continue

            variance_returns = df["Log_Return"].var()
            total_log_return = df["Log_Return"].sum()
            total_return = np.exp(total_log_return) - 1

            sheet_name = ticker[:31]
            df.to_excel(writer, sheet_name=sheet_name)

            workbook = writer.book
            worksheet = writer.sheets[sheet_name]

            n_rows = len(df) + 1
            summary_start_row = n_rows + 1

            worksheet.write(summary_start_row, 0, "Variance of log returns")
            worksheet.write(summary_start_row, 1, variance_returns)

            worksheet.write(summary_start_row + 1, 0, "Total return (period)")
            worksheet.write(summary_start_row + 1, 1, total_return)

            percent_format = workbook.add_format({"num_format": "0.00%"})
            worksheet.write(summary_start_row + 1, 1, total_return, percent_format)

    print(f"Done. Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
