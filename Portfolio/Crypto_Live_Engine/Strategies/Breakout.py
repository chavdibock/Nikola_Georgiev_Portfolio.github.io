import pandas as pd
from BinanceBot.Helpers import model_storage as ms
from BinanceBot import SavedModels as sm


# from BinanceBot.Helpers.SlackBots import all_trades_bot as slack_trades

class Breakout:
    def __init__(self, symbol, df, params=None):
        """
        Initializes the strategy with a DataFrame and optional parameters.
        """
        self.df = df
        self.symbol = symbol
        self.params = params or {}
        self.latest = df.iloc[-1]

    def calculate_features(self):
        if self.df.empty or len(self.df) < 180:
            print("Insufficient data for feature calculation.", len(self.df))
            return pd.DataFrame()
        df = self.df.copy()
        df['MA'] = df['Close'].rolling(int(self.params.get('ma_window'))).mean()
        df['STD'] = df['Close'].rolling(int(self.params.get('vwap_window'))).std()
        df['ZScore'] = (df['Close'] - df['MA']) / df['STD']
        df['ATR'] = (df['Close'] - df['Close'].shift(1)).abs().rolling(14).mean()
        df['Position'] = 0
        df['Target'] = 0
        return df

    """{
        "rr": 1.6788062303080964,
        "atr_mult": 1.4425524898800903,
        "max_hold": 13,
        "z_thresh": 0.01,
        "ma_window": 44,
        "vwap_window": 49
    }"""

    def entry_signal(self):
        features = self.calculate_features()
        row = features.iloc[-1]
        z_thresh = self.params.get('z_thresh')
        z = row['ZScore']

        # brekout strategy can be used with hawkes model
        # mean reversion can be enhanced with stationarity check
        # model_name = f"mean_reversion_{self.symbol}"
        # mean_reversion_model = ms.ModelStorage()
        # model = mean_reversion_model.load_model(model_name)

        # Example logic: Bollinger Band + MA dip ;lus probability of a profitable trade
        if z > z_thresh:
            # slack_trades.send_trade_message(self.symbol, row['Close'], "Sell")
            return True, 'buy'
        elif z < -z_thresh:
            return True, 'sell'
            # slack_trades.send_trade_message(self.symbol, row['Close'], "Buy")

        return False, None

    def exit_signal(self, current_position):
        # strategy uses a fixed rr stop loss and take profit
        pass


def breakout_strategy(df, z_thresh, ma_window, vwap_window, rr, atr_mult=0.5, max_hold=10, slippage=0.0005):
    ma_window = int(ma_window)
    vwap_window = int(vwap_window)
    df = df.copy()
    df['MA'] = df['Close'].rolling(ma_window).mean()
    df['STD'] = df['Close'].rolling(vwap_window).std()
    df['ZScore'] = (df['Close'] - df['MA']) / df['STD']
    df['ATR'] = (df['Close'] - df['Close'].shift(1)).abs().rolling(14).mean()
    df['Position'] = 0
    df['Target'] = 0

    in_position = 0
    entry_price = None
    entry_index = None
    entry_i = None
    cooldown = 0

    for i in range(1, len(df)):
        if cooldown > 0:
            cooldown -= 1
            continue

        row = df.iloc[i]
        z = row['ZScore']
        price = row['Close']
        atr = row['ATR']

        if in_position == 0:
            if z > z_thresh:
                in_position = 1
                entry_price = price * (1 + slippage)
                entry_index = df.index[i]
                entry_i = i
            elif z < -z_thresh:
                in_position = -1
                entry_price = price * (1 - slippage)
                entry_index = df.index[i]
                entry_i = i

        elif in_position == 1:
            if price >= entry_price + rr * atr or price <= entry_price - atr_mult * atr or (i - entry_i) >= max_hold:
                profit = price - entry_price
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0
                cooldown = 2

        elif in_position == -1:
            if price <= entry_price - rr * atr or price >= entry_price + atr_mult * atr or (i - entry_i) >= max_hold:
                profit = entry_price - price
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0
                cooldown = 2

        df.iloc[i, df.columns.get_loc('Position')] = in_position

    df['Target'] = df['Target'].fillna(0).astype(int)
    return df.dropna()
