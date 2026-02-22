#!/usr/bin/env python3
"""
Classify stocks using valuation z-scores (favoring lower p_e, p_b, p_cash)
and then fetch 1-month daily historical data for non-Hold stocks
to compute variance and covariance of returns.

Usage:
    python classify_stocks.py
Input:
    stocks.csv  (must include: Symbol,Name,p_e,p_b,p_cash,...)
Output:
    stocks_scored.csv          # classification results
    returns_stats.csv          # variance and covariance matrix (for Buy/Sell stocks)
"""

import os
import sys
import math
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# External package
import yfinance as yf

INPUT_FILE = "enriched_stocks.csv"
OUTPUT_FILE = "stocks_scored.csv"
RETURNS_FILE = "returns_stats.csv"
REQUIRED = ["p_e", "p_b", "p_cash"]


# ---------- Helper functions ----------
def iqr_cap(s: pd.Series) -> pd.Series:
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    if not np.isfinite(iqr) or iqr == 0:
        return s
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return s.clip(lower=lo, upper=hi)


def robust_z(s: pd.Series) -> pd.Series:
    med = s.median(skipna=True)
    mad = (np.abs(s - med)).median(skipna=True)
    if not np.isfinite(mad) or mad == 0:
        mu, sd = s.mean(skipna=True), s.std(skipna=True, ddof=0)
        if not np.isfinite(sd) or sd == 0:
            return pd.Series(np.zeros(len(s)), index=s.index)
        return (s - mu) / sd
    return 0.67448975 * (s - med) / mad


def classify_from_z(z: pd.Series) -> pd.Series:
    """Buy if top 20% (z ≥ 0.84), Sell if bottom 20% (z ≤ -0.84), else Hold."""

    def lab(val):
        if pd.isna(val): return "Hold"
        if val >= 1.7: return "Buy"
        if val <= -1.7: return "Sell"
        return "Hold"

    return z.apply(lab)


# ---------- Step 1: Classification ----------
if not os.path.exists(INPUT_FILE):
    print(f"ERROR: '{INPUT_FILE}' not found.")
    sys.exit(1)

df = pd.read_csv(INPUT_FILE)
df["Last Sale"] = (
    df["Last Sale"]
    .astype(str)  # make sure it's string type
    .str.replace("$", "", regex=False)  # remove the dollar sign
    .str.replace(",", "", regex=False)  # remove commas (if any)
    .astype(float)  # convert to numeric (float64)
)
df = df[df["Last Sale"] >= 2.30].copy()
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    print(f"ERROR: Missing columns: {missing}")
    sys.exit(1)

for c in REQUIRED:
    df[c] = pd.to_numeric(df[c], errors="coerce")
    capped = iqr_cap(df[c])
    z = robust_z(capped)
    df[f"z_{c}"] = -z  # invert so lower ratios = better

# Composite and z-standardize
df["quality_score"] = df[[f"z_{c}" for c in ["p_e", "p_b", "p_cash"]]].mean(axis=1, skipna=True)
df["quality_z"] = robust_z(df["quality_score"])
df["quality_rank"] = df["quality_score"].rank(method="average", ascending=False)
df["classification"] = classify_from_z(df["quality_z"])

# Save classification
df.to_csv(OUTPUT_FILE, index=False)
print(f"Saved classification results to {OUTPUT_FILE}")

# ---------- Step 2: Historical data for Buy/Sell ----------
df = pd.read_csv("stocks_scored.csv")
targets = df.loc[df["classification"].isin(["Buy", "Sell"]), "Symbol"].dropna().unique().tolist()

if not targets:
    print("No Buy/Sell stocks to analyze.")
    sys.exit(0)

print(f"Fetching 1-month daily data for {len(targets)} symbols...")

end = datetime.now()
start = end - timedelta(days=30)

data = {}
for sym in targets:
    try:
        hist = yf.download(tickers=sym, start=start, end=end, interval="1d")
        if not hist.empty:
            returns = hist["Close"].pct_change().dropna()
            data[sym] = returns
    except Exception as e:
        print(f"⚠️ Could not fetch {sym}: {e}")

if not data:
    print("No valid price data fetched.")
    sys.exit(0)

returns_df = pd.concat(data.values(), axis=1)
returns_df.columns = list(data.keys())

# Keep only columns with at least 2 data points
returns_df = returns_df.dropna(axis=1, thresh=2)

# Drop rows that are all-NaN (dates where nothing traded)
returns_df = returns_df.dropna(how="all")

if returns_df.empty:
    print("No valid return data available.")
    sys.exit(0)

# Variance and covariance
variances = returns_df.var()
cov_matrix = returns_df.cov()
avg_daily_ret = returns_df.mean()

class_map = (
    df[["Symbol", "classification"]]
    .dropna(subset=["Symbol"])
    .drop_duplicates(subset=["Symbol"])
    .set_index("Symbol")["classification"]
)
# Combine results
summary = pd.DataFrame({
    "variance": variances,
    "avg_daily_return": avg_daily_ret,
})
summary.index.name = "Symbol"
summary["classification"] = summary.index.to_series().map(class_map)

# Write variance + covariance
with pd.ExcelWriter(RETURNS_FILE.replace(".csv", ".xlsx")) as writer:
    summary.to_excel(writer, sheet_name="Variance")
    cov_matrix.to_excel(writer, sheet_name="Covariance")

print(f"Saved variance and covariance to {RETURNS_FILE.replace('.csv', '.xlsx')}")
