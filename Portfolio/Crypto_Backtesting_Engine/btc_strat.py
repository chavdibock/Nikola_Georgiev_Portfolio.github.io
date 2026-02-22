import os
import kagglehub
import pandas as pd
import numpy as np
from hmmlearn import hmm
import xgboost as xgb
import matplotlib.pyplot as plt

# --- Download BTC Daily Data ---
print("Downloading dataset from Kaggle...")
path = kagglehub.dataset_download("novandraanugrah/bitcoin-historical-datasets-2018-2024")
print("Path to dataset files:", path)

# Take just the first CSV file in the directory
csv_files_in_path = [f for f in os.listdir(path) if f.endswith('.csv')]
if not csv_files_in_path:
    raise RuntimeError("No CSV files found in dataset directory.")

first_csv_file = csv_files_in_path[0]
print(f"\nReading first CSV file: {first_csv_file}")

file_path = os.path.join(path, first_csv_file)
btc = pd.read_csv(file_path)
print(f"Loaded {len(btc)} rows from {first_csv_file}")

# Process datetime and set index
if 'Open time' in btc.columns:
    btc['Timestamp'] = pd.to_datetime(btc['Open time'], errors='coerce')
    btc.dropna(subset=['Timestamp'], inplace=True)
    btc.set_index('Timestamp', inplace=True)
else:
    raise RuntimeError("CSV does not contain 'Open time' column.")

# --- Feature Engineering ---
def calculate_features(df):
    df = df.copy()
    df['MA20'] = df['Close'].rolling(20).mean()
    df['ROC_MA20'] = df['MA20'].pct_change(5)

    # VWAP
    df['Typical Price'] = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (df['Typical Price'] * df['Volume']).rolling(20).sum() / df['Volume'].rolling(20).sum()
    df['ROC_VWAP'] = df['VWAP'].pct_change(5)

    # Bollinger Bands
    df['STD20'] = df['Close'].rolling(20).std()
    df['UpperBand'] = df['MA20'] + (df['STD20'] * 2)
    df['LowerBand'] = df['MA20'] - (df['STD20'] * 2)
    df['BandWidth'] = (df['UpperBand'] - df['LowerBand']) / df['MA20']

    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Additional Features - Volume based
    df['volume_change'] = df['Volume'].pct_change()
    df['buy_volume_ratio'] = df['Taker buy base asset volume'] / df['Volume']

    # Trade Activity Features
    df['avg_trade_size'] = df['Volume'] / df['Number of trades']
    df['trade_intensity'] = df['Number of trades'] / df['Volume']

    return df

features_raw_df = calculate_features(btc)
features_df = features_raw_df.dropna()

# --- Market Regime Detection with HMM ---
hmm_data = features_df[['ROC_MA20', 'ROC_VWAP', 'BandWidth', 'RSI']].values

hmm_model = hmm.GaussianHMM(
    n_components=4,
    covariance_type="diag",
    n_iter=100,
    random_state=42
)
hmm_model.fit(hmm_data)
features_df.loc[:, 'MarketRegime'] = hmm_model.predict(hmm_data)

# --- Target Variable ---
features_df.loc[:, 'Returns'] = features_df['Close'].pct_change()
features_df.loc[:, 'Target'] = np.where(features_df['Returns'].shift(-1) > 0, 1, 0)
features_df.dropna(inplace=True)

# --- Prepare Data for XGBoost ---
feature_cols = ['ROC_MA20', 'ROC_VWAP', 'BandWidth', 'RSI', 'MarketRegime',
                'volume_change', 'buy_volume_ratio', 'avg_trade_size', 'trade_intensity']

X = features_df[feature_cols].copy()
y = features_df['Target'].copy()

# Clean the feature matrix: replace inf/-inf and drop NaNs
X.replace([np.inf, -np.inf], np.nan, inplace=True)
X.dropna(inplace=True)
y = y.loc[X.index]  # Align y with cleaned X

# Time-series split (preserve temporal order)
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# Train XGBoost
model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=1000,
    learning_rate=0.01,
    max_depth=4,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=False
)

# --- Predict & Signal Generation ---
features_df.loc[:, 'Prediction'] = np.nan  # Initialize full column
features_df.loc[X.index, 'Prediction'] = model.predict_proba(X)[:, 1]

features_df.loc[:, 'Signal'] = 0
features_df.loc[X.index, 'Signal'] = 0
features_df.loc[X.index, 'Signal'] = np.where(
    features_df.loc[X.index, 'Prediction'] > 0.6, 1,
    np.where(features_df.loc[X.index, 'Prediction'] < 0.4, -1, 0)
)

# --- Backtest Strategy ---
features_df.loc[:, 'StrategyReturns'] = features_df['Signal'].shift(1) * features_df['Returns']
features_df.loc[:, 'CumulativeReturns'] = (1 + features_df['StrategyReturns']).cumprod()
features_df.loc[:, 'BuyHold'] = (1 + features_df['Returns']).cumprod()

# --- Plot ---
plt.figure(figsize=(12, 6))
plt.title("BTC: ML Strategy vs Buy & Hold")
plt.plot(features_df['CumulativeReturns'], label='ML Strategy')
plt.plot(features_df['BuyHold'], label='Buy & Hold', alpha=0.6)
plt.ylabel("Cumulative Return")
plt.xlabel("Date")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()
