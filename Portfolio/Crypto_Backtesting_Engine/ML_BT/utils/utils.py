from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, classification_report
import matplotlib.pyplot as plt
# start="2005-01-01", end="2025-05-25", interval="1d"
import yfinance as yf
import pandas as pd
import talib
from sklearn.model_selection import train_test_split

import numpy as np
import shap


def show_importance(model, X_test):
    explainer = shap.Explainer(model)
    shap_values = explainer(X_test)

    # Summary plot
    shap.summary_plot(shap_values, X_test)

    # For a single prediction explanation:
    shap.plots.waterfall(shap_values[0])


def get_data(symbol, period, start_date, end_date):
    df = yf.download(symbol, start=start_date, end=end_date, interval=period)
    df = df.reset_index()

    # Remove multi-index if present
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)

    # Shift OHLC columns for prev day info
    df['prev_day_open'] = df['Open'].shift(1)
    df['prev_day_high'] = df['High'].shift(1)
    df['prev_day_low'] = df['Low'].shift(1)
    df['prev_day_close'] = df['Close'].shift(1)

    # Calculate actual return for the current day (in percent)
    df['actual_return'] = (df['Close'] - df['Open']) / df['Open'] * 100
    df['prev_high_low'] = (df['prev_day_high'] - df['prev_day_low']) / df['prev_day_high'] * 100
    # Calculate return_1d (previous day's return)
    df['return_1d'] = (df['prev_day_close'] - df['prev_day_open']) / df['prev_day_open'] * 100
    df["gap"] = df["Open"] - df["prev_day_close"]
    df["gap_prc"] = (df["Open"] - df["prev_day_close"]) / df["prev_day_close"] * 100
    # Calculate multi-day returns ending yesterday
    for days in range(2, 6):  # 2 to 5
        prev_idx = df.index - 1
        start_idx = df.index - days
        close_yesterday = df['Close'].shift(1)
        close_n_days_ago = df['Open'].shift(days)
        df[f'return_{days}d'] = (close_yesterday - close_n_days_ago) / close_n_days_ago * 100

    # Use only data up to previous day for indicators
    close_shifted = df['Close'].shift(1)

    df['SMA_10'] = talib.SMA(close_shifted, timeperiod=10)
    df['SMA_20'] = talib.SMA(close_shifted, timeperiod=20)
    df['SMA_50'] = talib.SMA(close_shifted, timeperiod=50)
    df['SMA_100'] = talib.SMA(close_shifted, timeperiod=100)
    df['MACD'], df['MACD_signal'], df['MACD_hist'] = talib.MACD(
        close_shifted, fastperiod=9, slowperiod=21, signalperiod=9
    )
    df['RSI_21'] = talib.RSI(close_shifted, timeperiod=21)

    # Rolling windows for indicator data (always excludes today)
    for period in [10, 20, 50, 100]:
        colname = f"SMA_{period}_Data"
        df[colname] = [
            list(zip(
                df.loc[i - period:i - 1, 'Date'],
                df.loc[i - period:i - 1, 'Close']
            )) if i >= period else None
            for i in range(len(df))
        ]
    # RSI data window
    df['RSI_21_Data'] = [
        list(zip(
            df.loc[i - 21:i - 1, 'Date'],
            df.loc[i - 21:i - 1, 'Close']
        )) if i >= 21 else None
        for i in range(len(df))
    ]

    # Drop rows with NaNs in key features (handle shifting and rolling windows)
    df = df.dropna()

    return df


def save_to_excel(df, symbol):
    # indicator_cols = [
    #     "Date", 'SMA_10', 'SMA_20', 'SMA_50', 'SMA_100',
    #     'prev_day_open', 'prev_day_high', 'prev_day_low', 'prev_day_close', "gap_prc", "prev_high_low", "actual_return",
    #     'return_1d', 'return_2d', 'return_3d', 'return_4d', 'return_5d', 'MACD', 'MACD_signal', 'MACD_hist', 'RSI_21'
    # ]

    df.to_excel(f"{symbol}_features.xlsx", index=False)
    # df.to_excel(f"{symbol}_dataset.xlsx", index=False)


def plot_indicators(df, symbol):
    plt.figure(figsize=(16, 10))

    # Plot Close price and SMAs
    plt.subplot(3, 1, 1)
    plt.plot(df.index, df['Close'], label='Close', linewidth=1)
    plt.plot(df.index, df['SMA_10'], label='SMA 10')
    plt.plot(df.index, df['SMA_20'], label='SMA 20')
    plt.plot(df.index, df['SMA_50'], label='SMA 50')
    plt.plot(df.index, df['SMA_100'], label='SMA 100')
    plt.title(f"{symbol} Price and SMA")
    plt.legend()
    plt.grid(True)

    # Plot MACD and Signal
    plt.subplot(3, 1, 2)
    plt.plot(df.index, df['MACD'], label='MACD')
    plt.plot(df.index, df['MACD_signal'], label='Signal')
    plt.bar(df.index, df['MACD_hist'], label='Hist', alpha=0.3)
    plt.title("MACD")
    plt.legend()
    plt.grid(True)

    # Plot RSI
    plt.subplot(3, 1, 3)
    plt.plot(df.index, df['RSI_21'], label='RSI 21', color='purple')
    plt.axhline(70, color='red', linestyle='--', linewidth=0.8)
    plt.axhline(30, color='green', linestyle='--', linewidth=0.8)
    plt.title("RSI (21)")
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.show()


def split_to_sets(df, cols, predict):
    y = df[predict]
    training_set = df[cols]
    # print(training_set)
    X_train, X_test, y_train, y_test = train_test_split(training_set, y, test_size=0.2, random_state=42, shuffle=False)
    return X_train, X_test, y_train, y_test


def plot_results(dates, actuals, predictions):
    results_df = pd.DataFrame({
        'Date': dates,
        'Actual': actuals,
        'Predicted': predictions
    }).set_index('Date')

    mse = mean_squared_error(results_df['Actual'], results_df['Predicted'])
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(results_df['Actual'], results_df['Predicted'])
    r2 = r2_score(results_df['Actual'], results_df['Predicted'])
    print("Sliding Window Evaluation:")
    print(f"  MSE: {mse:.5f}")
    print(f"  RMSE: {rmse:.5f}")
    print(f"  MAE: {mae:.5f}")
    print(f"  R² Score: {r2:.5f}")

    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(results_df['Actual'], label='Actual')
    plt.plot(results_df['Predicted'], label='Predicted', linestyle='--')
    plt.title("Sliding Window Prediction: Actual vs Predicted")
    plt.xlabel("Date")
    plt.ylabel("Target Value")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    symbol = " AAPL"
    period = "1d"
    start_date = "2005-01-01"
    end_date = "2025-05-25"

    data = get_data(symbol, period, start_date, end_date)

    print(data)

    # plot_indicators(data, symbol)
