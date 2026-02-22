import itertools

import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, GridSearchCV
import matplotlib.pyplot as plt
from scipy import stats


# Load data from Binance Web API (not the client)
def load_data(symbol, limit=100080):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": '15m',
        "limit": limit
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data for {symbol}: {response.text}")

    data = response.json()
    cols = ['openTime', 'open', 'high', 'low', 'close', 'volume',
            'closeTime', 'quoteAssetVolume', 'tradeCount',
            'takerVolume', 'takerAmount', 'ignore']

    df = pd.DataFrame(data, columns=cols)
    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    df.set_index('openTime', inplace=True)
    df = df[['close', 'volume']].rename(columns={'close': 'Close', 'volume': 'Volume'})
    return df


def calculate_mfi(df, window=14):
    typical_price = (df['Close'] + df['Close'].rolling(1).max() + df['Close'].rolling(1).min()) / 3
    money_flow = typical_price * df['Volume']
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0.0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0.0)
    mfr = positive_flow.rolling(window).sum() / (negative_flow.rolling(window).sum() + 1e-9)
    mfi = 100 - (100 / (1 + mfr))
    return mfi

def get_features(df):
    df['MA'] = df['Close'].rolling(30).mean()
    df['Rolling_VWAP'] = (df['Close'] * df['Volume']).rolling(100).sum() / df['Volume'].rolling(100).sum()
    df['STD'] = df['Close'].rolling(20).std()
    df['MFI'] = calculate_mfi(df)

    df['Upper'] = df['Rolling_VWAP'] + 1.5 *  df['STD']
    df['Lower'] = df['Rolling_VWAP'] - 1.5 *  df['STD']
    df['diff'] = df['Rolling_VWAP'] - df['MA']
    df['diff_zscore'] = (df['diff'] - df['diff'].rolling(20).mean()) / (df['diff'].rolling(50).std() + 1e-8)

    df['MA'] = df['MA'].pct_change(5)
    df['ROC_VWAP'] = df['Rolling_VWAP'].pct_change(5)

    df['Close'] = df['Close'].astype(float)
    df['returns'] = df['Close'].pct_change()
    df['volatility'] = df['returns'].rolling(window=10).std()
    df['momentum'] = df['Close'] / df['Close'].shift(10) - 1
    df['mean'] = df['Close'].rolling(window=20).mean()
    df['upper'] = df['mean'] + 2 * df['volatility']
    df['lower'] = df['mean'] - 2 * df['volatility']
    df.dropna(inplace=True)
    return df


def mean_reversion(df, threshold=2.0, vwap_window=100, mfi_upper=80, mfi_lower=20, zscore_limit=1.5):
    df = df.copy()
    df['Position'] = 0
    df['Target'] = 0
    in_position = 0
    entry_price = None
    entry_index = None

    for i in range(1, len(df)):
        row = df.iloc[i]

        if in_position == 0 and row['Close'] < row['Lower'] and row['MFI'] < mfi_lower and abs(row['diff_zscore']) > zscore_limit:
            in_position = 1
            entry_price = row['Close']
            entry_index = df.index[i]

        elif in_position == 0 and row['Close'] > row['Upper'] and row['MFI'] > mfi_upper and abs(row['diff_zscore']) > zscore_limit:
            in_position = -1
            entry_price = row['Close']
            entry_index = df.index[i]

        elif in_position == 1 and row['Close'] > row['Rolling_VWAP']:
            profit = row['Close'] - entry_price
            df.at[entry_index, 'Target'] = int(profit > 0)
            in_position = 0

        elif in_position == -1 and row['Close'] < row['Rolling_VWAP']:
            profit = entry_price - row['Close']
            df.at[entry_index, 'Target'] = int(profit > 0)
            in_position = 0

        df.iloc[i, df.columns.get_loc('Position')] = in_position

    df['Target'] = df['Target'].fillna(0).astype(int)
    return df

# Revised Breakout Strategy
def breakout_strategy(df, z_thresh=1.5):
    df['Position'] = 0
    df['Target'] = 0
    in_position = 0
    entry_price = None
    entry_index = None

    for i in range(1, len(df)):
        row = df.iloc[i]

        if in_position == 0:
            if row['diff_zscore'] > z_thresh:
                in_position = 1
                entry_price = row['Close']
                entry_index = df.index[i]
            elif row['diff_zscore'] < -z_thresh:
                in_position = -1
                entry_price = row['Close']
                entry_index = df.index[i]

        elif in_position == 1:
            if row['diff_zscore'] < 0:
                profit = row['Close'] - entry_price
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0

        elif in_position == -1:
            if row['diff_zscore'] > 0:
                profit = entry_price - row['Close']
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0

        df.iloc[i, df.columns.get_loc('Position')] = in_position

    df['Target'] = df['Target'].fillna(0).astype(int)
    return df

# Mean Reversion Optimizer
def optimise_advanced_mean_reversion(df):
    threshold_range = [1.2, 1.5, 1.8, 2.0, 2.2]
    mfi_upper_range = [70, 75, 80, 85, 90]
    mfi_lower_range = [10, 15, 20, 25]
    zscore_range = [-1, -0.5, 0, 0.5, 1]

    best_score = -np.inf
    best_params = {}

    for threshold, mfi_upper, mfi_lower, zscore_limit in itertools.product(
            threshold_range, mfi_upper_range, mfi_lower_range, zscore_range):

        # Skip invalid configs
        if mfi_lower >= mfi_upper:
            continue

        temp = mean_reversion(df.copy(), threshold=threshold,
                              mfi_upper=mfi_upper,
                              mfi_lower=mfi_lower,
                              zscore_limit=zscore_limit)

        returns = temp['Position'].shift(1) * temp['returns']
        score = returns.sum()

        if score > best_score:
            best_score = score
            best_params = {
                'threshold': threshold,
                'mfi_upper': mfi_upper,
                'mfi_lower': mfi_lower,
                'zscore_limit': zscore_limit
            }

    return best_params, best_score

# Breakout Strategy Optimizer
def optimise_breakout_strategy(df, z_min=-2.0, z_max=2.0, steps=20):
    z_thresholds = np.linspace(z_min, z_max, steps)

    best_score = -np.inf
    best_thresh = None

    for thresh in z_thresholds:
        temp = df.copy()
        temp['Position'] = 0
        temp['Target'] = 0
        result = breakout_strategy(temp, z_thresh=thresh)
        returns = result['Position'].shift(1) * result['returns']
        score = returns.sum()
        if score > best_score:
            best_score = score
            best_thresh = thresh

    return best_thresh, best_score


# Strategy Comparison
def compare_strategies(df):
    df_mr = df.copy()
    df_br = df.copy()

    best_mr, _ = optimise_advanced_mean_reversion(df_mr)
    best_br, _ = optimise_breakout_strategy(df_br)

    mr_result = mean_reversion(df_mr, best_mr)
    br_result = breakout_strategy(df_br, z_thresh=best_br)

    mr_returns = mr_result['Position'].shift(1) * mr_result['returns']
    br_returns = br_result['Position'].shift(1) * br_result['returns']

    cum_mr = mr_returns.cumsum()
    cum_br = br_returns.cumsum()

    if cum_mr > cum_br:
        return cum_mr, "mean reversion"
    else:
        return cum_br, "breakout"



def test_strategy_significance(returns, alpha=0.05):
    returns = returns.dropna()
    t_stat, p_value_two_sided = stats.ttest_1samp(returns, popmean=0)

    # Convert to one-sided p-value (H1: mean > 0)
    if t_stat > 0:
        p_value_one_sided = p_value_two_sided / 2
    else:
        p_value_one_sided = 1 - (p_value_two_sided / 2)

    print(f"\nOne-sided t-test results:")
    print(f"  t-statistic: {t_stat:.4f}")
    print(f"  p-value (one-sided): {p_value_one_sided:.4f}")
    if p_value_one_sided < alpha:
        print(f"  ✅ Statistically significant at alpha = {alpha}; you may consider trading it.")
    else:
        print(f"  ❌ Not statistically significant at alpha = {alpha}; avoid trading.")


def bayesian_optimise():
    db = MySQLDatabase()
    coins = Coins.CoinRepository(db)
    all_coins = coins.get_all_coins()

    for symbol in all_coins:
        symbol = symbol.get("symbol")
        data = load_data(symbol)

        best_strategy = compare_strategies(data)
        print(best_strategy)
        if test_strategy_significance(result_df['Strategy Returns']):
            info = coins.update_strategy_info_by_symbol(symbol, best_strategy.strategy_type, best_strategy.params, True, total_return)
            #update in database
        else:
            info = coins.update_strategy_info_by_symbol(symbol, None, None, False, None)
            return [], []




if __name__ == "__main__":
    df = load_data('BTCUSDT')  # 15m data
    df = get_features(df)

    best_strategy, strategy_type = compare_strategies(df)

    if strategy_type == "mean_reversion":
        strategy_result = mean_reversion(df.copy(), best_mr)
    if strategy_type == "breakout":
        strategy_result = breakout_strategy(df.copy(), best_br)



    # Get returns
    strategy_result = mr_result['Position'].shift(1) * mr_result['returns']

    # Run t-tests
    test_strategy_significance(strategy_result)
    print("Best Strategy: ", strategy_type)

