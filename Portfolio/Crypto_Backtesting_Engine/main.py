import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import accuracy_score
import matplotlib.pyplot as plt
import pandas_ta as ta
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score, classification_report
import numpy as np

if __name__ == '__main__':
    data = yf.download('IBM', start="2019-01-01", end="2023-06-30")

    # Display the data
    data.tail()


    df = pd.read_csv('Prev_Data/SOL/sol_3m/SOLUSDT-3m-2024-01.csv', sep=',', encoding='utf-8', header=0)
    pd.set_option('display.max_columns', None)
    # df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')

    # # Extract time-based features
    # df['hour'] = df['open_time'].dt.hour
    # df['day_of_week'] = df['open_time'].dt.dayofweek

    # # Optional: drop original timestamp if not needed
    # df.drop('open_time', axis=1, inplace=True)
    # df['target'] = df['close'].shift(-1)  # Predict the next close
    # df = df.dropna()  # Drop last row (NaN target)
    # features = ['open', 'low', 'volume', 'quote_volume', 'count',
    #             'taker_buy_volume', 'taker_buy_quote_volume', 'hour', 'day_of_week']

    # X = df[features]
    # y = df['target']
    training_set = pd.DataFrame(
        {
            "Open-Close-Prc": (df.open - df.close) / df.open,
            "High-Low-Prc": (df.high - df.low) / df.low,
            "Ma_5": df.close.rolling(5).mean()
        }
    )
    y = np.where(df['close'].shift(-1) > df['close'], 1, -1)
    print(df["close"])
    print(y)
    X_train, X_test, y_train, y_test = train_test_split(training_set, y, test_size=0.2, random_state=42)
    # model = DecisionTreeRegressor(max_depth=5, random_state=42)
    model_random_forest = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model_random_forest.fit(X_train, y_train)
    # model.fit(X_train, y_train)

    # y_pred_des_tree = model.predict(X_test)
    y_pred_random_for = model_random_forest.predict(X_test)

    # mse_random_tree = mean_squared_error(y_test, y_pred_des_tree)
    mse_random_for = mean_squared_error(y_test, y_pred_random_for)
    # print("Mean Squared Error Des Tree:", mse_random_tree)
    print("Mean Squared Error random_for:", mse_random_for)
    mse = mean_squared_error(y_test, y_pred_random_for)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(y_test, y_pred_random_for)
    r2 = r2_score(y_test, y_pred_random_for)
    # Print formatted output
    print("📊 Model Performance Metrics:")
    print(f"  Mean Squared Error (MSE):      {mse:.5f}")
    print(f"  Root Mean Squared Error (RMSE): {rmse:.5f}")
    print(f"  Mean Absolute Error (MAE):      {mae:.5f}")
    print(f"  R² Score:                        {r2:.5f}")
    # importances = model_random_forest.feature_importances_
    # feature_names = X.columns
    #
    # # Create a DataFrame for easy plotting
    # feat_df = pd.DataFrame({'Feature': feature_names, 'Importance': importances})
    # feat_df = feat_df.sort_values(by='Importance', ascending=False)
    #
    # # Plot
    # plt.figure(figsize=(10, 6))
    # plt.barh(feat_df['Feature'], feat_df['Importance'])
    # plt.xlabel('Importance')
    # plt.title('Feature Importances in DecisionTreeRegressor')
    # plt.gca().invert_yaxis()  # Highest on top
    # plt.tight_layout()
    # plt.show()
    # Create a comparison DataFrame
    comparison_df = pd.DataFrame({
        'Actual': y_test,
        'Predicted': y_pred_random_for
    })
    comparison_df['Error'] = abs(comparison_df['Actual'] - comparison_df['Predicted'])
    comparison_df = comparison_df.sort_values(by='Error', ascending=False)
    # Optionally reset the index if needed
    comparison_df = comparison_df.reset_index(drop=True)

    # Show first few rows
    print(comparison_df.head(10))
    plt.ion()  # Enable interactive mode

    plt.figure(figsize=(10, 5))
    plt.plot(comparison_df['Actual'], label='Actual')
    plt.plot(comparison_df['Predicted'], label='Predicted', linestyle='--')
    plt.title('Actual vs Predicted')
    plt.legend()
    plt.grid(True)

    plt.show(block=True)  # <-- This holds the window open
