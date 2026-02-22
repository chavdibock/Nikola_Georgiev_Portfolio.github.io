import os
import kagglehub
import pandas as pd
import numpy as np
from hmmlearn import hmm
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score
)
from backtesting import Backtest, Strategy

file_path = "C:/Users/User/PycharmProjects/quant/Prev_Data/SOL/sol_1d/SOLUSDT-1d-2024-01.csv"
btc = pd.read_csv(file_path)
print(btc.columns)
# --- Datetime Handling ---
if 'open_time' in btc.columns:
    btc['Timestamp'] = pd.to_datetime(btc['open_time'], errors='coerce')
    btc.dropna(subset=['Timestamp'], inplace=True)
    btc.set_index('Timestamp', inplace=True)
else:
    raise RuntimeError("CSV does not contain 'Open time' column.")


# --- Feature Engineering ---
def calculate_features(df):
    df = df.copy()
    df['MA20'] = df['close'].rolling(20).mean()
    df['ROC_MA20'] = df['MA20'].pct_change(5)
    df['Typical Price'] = (df['high'] + df['low'] + df['close']) / 3
    df['VWAP'] = (df['Typical Price'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
    df['ROC_VWAP'] = df['VWAP'].pct_change(5)
    df['STD20'] = df['close'].rolling(20).std()
    df['UpperBand'] = df['MA20'] + (df['STD20'] * 2)
    df['LowerBand'] = df['MA20'] - (df['STD20'] * 2)
    df['BandWidth'] = (df['UpperBand'] - df['LowerBand']) / df['MA20']
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['volume_change'] = df['volume'].pct_change()
    return df


features_df = calculate_features(btc)
features_df = features_df.dropna()

# --- Market Regime Detection ---
hmm_data = features_df[['ROC_MA20', 'ROC_VWAP', 'BandWidth', 'RSI']].values
hmm_model = hmm.GaussianHMM(n_components=4, covariance_type="diag", n_iter=100, random_state=42)
hmm_model.fit(hmm_data)
features_df['MarketRegime'] = hmm_model.predict(hmm_data)

# --- Target Variable ---
features_df['Returns'] = features_df['close'].pct_change()
features_df['Target'] = np.where(features_df['Returns'].shift(-1) > 0, 1, 0)
features_df.dropna(inplace=True)

# --- Prepare for ML ---
feature_cols = ['ROC_MA20', 'ROC_VWAP', 'BandWidth', 'RSI', 'MarketRegime',
                'volume_change']
X = features_df[feature_cols].copy()
y = features_df['Target'].copy()
X.replace([np.inf, -np.inf], np.nan, inplace=True)
X.dropna(inplace=True)
y = y.loc[X.index]

# --- Time-series Split ---
split_idx = int(len(X) * 0.8)
X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

# --- Train XGBoost ---
model = xgb.XGBClassifier(
    objective='binary:logistic',
    n_estimators=1000,
    learning_rate=0.01,
    max_depth=4,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

# --- Prediction & Signal Generation ---
features_df['Prediction'] = np.nan
features_df.loc[X.index, 'Prediction'] = model.predict_proba(X)[:, 1]

features_df['Signal'] = 0
features_df.loc[X.index, 'Signal'] = np.where(
    features_df.loc[X.index, 'Prediction'] > 0.6, 1,
    np.where(features_df.loc[X.index, 'Prediction'] < 0.4, -1, 0)
)
bt_data = features_df.iloc[split_idx:].copy()
bt_data = bt_data[['open', 'high', 'low', 'close', 'Signal']].copy()
bt_data.columns = ['Open', 'High', 'Low', 'Close', 'Signal']
bt_data = bt_data.dropna()

class MLSignalStrategy(Strategy):
    def init(self):
        self.signal = self.data.Signal

    def next(self):
        idx = len(self.data.Close) - 1
        current_signal = self.signal[idx]

        if current_signal == 1:
            if not self.position.is_long:
                self.position.close()
                self.buy()
        elif current_signal == -1:
            if not self.position.is_short:
                self.position.close()
                self.sell()
        else:
            self.position.close()

bt = Backtest(
    bt_data,
    MLSignalStrategy,
    cash=10000,
    commission=.005,
    exclusive_orders=True
)

output = bt.run()
bt.plot()
print(output)
# --- Test Metrics ---
y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

print("\n--- Model Performance on Test Set ---")
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.4f}")
print(f"Precision: {precision_score(y_test, y_pred):.4f}")
print(f"Recall:    {recall_score(y_test, y_pred):.4f}")
print(f"F1 Score:  {f1_score(y_test, y_pred):.4f}")
print(f"ROC AUC:   {roc_auc_score(y_test, y_proba):.4f}")

# --- Win Rate ---
test_signals = features_df.iloc[split_idx:].copy()
valid_signals = test_signals[test_signals['Signal'] != 0]
valid_signals['Correct'] = np.where(
    (valid_signals['Signal'] == 1) & (valid_signals['Returns'] > 0) |
    (valid_signals['Signal'] == -1) & (valid_signals['Returns'] < 0), 1, 0
)
win_rate = valid_signals['Correct'].mean()
print(f"\nStrategy Win Rate on Test Set: {win_rate:.2%}")
