from builtins import map

import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor, ExtraTreeRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, classification_report
import matplotlib.pyplot as plt

if __name__ == "__main__":

    # Example: reading your existing dataset
    df = yf.download('UEC', start="2022-01-01", end="2025-05-25")

    # Flatten multi-index columns if needed
    df.columns = df.columns.droplevel(1)
    # Parameters
    macd_fast = 9
    macd_slow = 21
    rsi_period = 14
    boll_len = 20
    boll_std = 2
    print(df)
    # Daily Return
    df['Return'] = (df['Close'] - df['Open']) / df['Open']

    # MACD
    ema_fast = df['Close'].ewm(span=macd_fast, adjust=False).mean()
    ema_slow = df['Close'].ewm(span=macd_slow, adjust=False).mean()
    df['MACD'] = ema_fast - ema_slow

    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    rolling_mean = df['Close'].rolling(window=boll_len).mean()
    rolling_std = df['Close'].rolling(window=boll_len).std()
    df['Boll_Upper'] = rolling_mean + (boll_std * rolling_std)
    df['Boll_Lower'] = rolling_mean - (boll_std * rolling_std)

    # Percent change from last close to current open
    df['Open_to_PrevClose_Pct'] = (df['Open'] - df['Close'].shift(1)) / df['Close'].shift(1)

    # Lagged daily returns
    for i in range(1, 6):
        df[f'Lagged_Return_{i}d'] = df['Return'].shift(i)

    # Lagged weekly returns (assuming 5 trading days/week)
    df['Lagged_Return_2w'] = df['Return'].shift(10)
    df['Lagged_Return_3w'] = df['Return'].shift(15)

    # Final dataset
    result = df[[
        'MACD', 'RSI', 'Boll_Upper', 'Boll_Lower', 'Open_to_PrevClose_Pct',
        'Lagged_Return_1d', 'Lagged_Return_2d', 'Lagged_Return_3d',
        'Lagged_Return_4d', 'Lagged_Return_5d', 'Lagged_Return_2w', 'Lagged_Return_3w',
    ]]
    result = result.dropna()

    X = result[[
        'MACD', 'RSI', 'Open_to_PrevClose_Pct',
        'Lagged_Return_1d', 'Lagged_Return_2d', 'Lagged_Return_3d',
        'Lagged_Return_4d', 'Lagged_Return_5d', 'Lagged_Return_2w', 'Lagged_Return_3w'
    ]]
    y = result["Lagged_Return_1d"].shift(-1)

    X = X.loc[y.dropna().index]
    y = y.dropna()

    rolling_window = 810  # training size (99 days)
    predictions = []
    actuals = []
    dates = []

    for i in range(rolling_window, len(X)):
        X_train = X.iloc[i - rolling_window:i]
        y_train = y.iloc[i - rolling_window:i]
        X_test = X.iloc[i:i + 1]
        y_test = y.iloc[i:i + 1]
        model = GradientBoostingRegressor(max_depth=10000, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)[0]
        # print("Day", y_test.index[0], "Actual Change: ", y_test.values[0], "Predicted: ", y_pred)
        predictions.append(y_pred)
        actuals.append(y_test.values[0])
        dates.append(y_test.index[0])

    # Convert to DataFrame for analysis
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
