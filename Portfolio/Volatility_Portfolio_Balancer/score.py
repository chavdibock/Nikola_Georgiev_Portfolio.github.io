#!/usr/bin/env python3
"""
Classify stocks from a CSV using robust z-scores on valuation ratios,
favoring lower p_e, p_b, p_cash (your stated bias).

Usage: python classify_stocks.py
Input:  stocks.csv  (must include columns: Symbol,Name,...,p_e,p_b,p_cash)
Output: stocks_scored.csv
"""

import os
import sys
import math
import pandas as pd
import numpy as np

INPUT_FILE = "enriched_stocks.csv"
OUTPUT_FILE = "stocks_scored.csv"
REQUIRED = ["p_e", "p_b", "p_cash"]

def iqr_cap(s: pd.Series) -> pd.Series:
    """Cap outliers using Tukey fences (1.5 * IQR)."""
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if not np.isfinite(iqr) or iqr == 0:
        return s
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    return s.clip(lower=lo, upper=hi)

def robust_z(s: pd.Series) -> pd.Series:
    """Median/MAD z-score scaled to be comparable to std-based z."""
    med = s.median(skipna=True)
    mad = (np.abs(s - med)).median(skipna=True)
    if not np.isfinite(mad) or mad == 0:
        # Fall back to mean/std if MAD is degenerate
        mu = s.mean(skipna=True)
        sd = s.std(skipna=True, ddof=0)
        if not np.isfinite(sd) or sd == 0:
            return pd.Series(np.zeros(len(s)), index=s.index)
        return (s - mu) / sd
    return 0.67448975 * (s - med) / mad

def classify_from_z(z: pd.Series) -> pd.Series:
    """
    Use cutoffs at ±0.84 (~80th/20th percentile of a normal distribution)
    to avoid any user-tuned thresholds.
    """
    def lab(val):
        if pd.isna(val):
            return "Hold"
        if val >= 0.84:
            return "Buy"
        if val <= -0.84:
            return "Sell"
        return "Hold"
    return z.apply(lab)

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: '{INPUT_FILE}' not found. Place your CSV as '{INPUT_FILE}'.", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(INPUT_FILE)

    # Ensure required columns exist
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        print(f"ERROR: Missing required columns: {missing}", file=sys.stderr)
        sys.exit(1)

    # Coerce to numeric
    for c in REQUIRED:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # IQR cap then robust z for each metric
    zcols = []
    for c in REQUIRED:
        capped = iqr_cap(df[c])
        z = robust_z(capped)
        df[f"z_{c}"] = -z  # invert so lower ratio => higher (better)
        zcols.append(f"z_{c}")

    # Composite = simple average of available z’s (no hard-coded weights)
    Z = df[zcols].to_numpy(dtype=float)
    with np.errstate(invalid='ignore'):
        comp = np.nanmean(Z, axis=1)  # if some metrics missing, average the rest
    df["quality_score"] = comp

    # Standardize composite to get a composite z (for classification)
    # Use robust z again to avoid tuning.
    comp_series = pd.Series(comp, index=df.index)
    comp_z = robust_z(comp_series)
    df["quality_z"] = comp_z

    # Rank (higher score ranks better). NaNs go to bottom.
    df["quality_rank"] = df["quality_score"].rank(method="average", ascending=False, na_option="bottom")

    # Classification
    df["classification"] = classify_from_z(comp_z)

    # Arrange output columns if present
    front = ["Symbol", "Name", "p_e", "p_b", "p_cash",
             "z_p_e", "z_p_b", "z_p_cash",
             "quality_score", "quality_z", "quality_rank", "classification"]
    out_cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
    df[out_cols].to_csv(OUTPUT_FILE, index=False)
    print(f"Saved: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
