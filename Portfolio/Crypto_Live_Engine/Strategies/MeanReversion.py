import pandas as pd
from BinanceBot.Helpers import model_storage as ms
from BinanceBot import SavedModels as sm


#Here we will load the staretgy parameters of the best startegy and use it to generate entry and exit signals.
class MeanReversion:
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

        window = self.params.get('window')
        window = int(window)
        df = self.df.copy()
        df['VWAP'] = (df['Close'] * df['Volume']).rolling(window).sum() / df['Volume'].rolling(window).sum()
        df['ATR'] = (df['Close'] - df['Close'].shift(1)).abs().rolling(window).mean()
        df['ROC_VWAP'] = df['VWAP'].pct_change(5)
        df['Position'] = 0
        df['Target'] = 0
        df['EMA9'] = df['Close'].ewm(span=7, adjust=False).mean()
        df['EMA9_DIFF'] = df['EMA9'].diff()

        df.dropna(inplace=True)
        return df

    def entry_signal(self):
        df = self.calculate_features()
        row = df.iloc[-1]
        prev = df.iloc[-2]
        price = row['Close']
        atr = row['ATR']
        threshold = self.params.get('threshold')

        #model_name = f"mean_reversion_{self.symbol}"
        #mean_reversion_model = ms.ModelStorage()
        #model = mean_reversion_model.load_model(model_name)


        # Example logic: Bollinger Band + MA dip ;lus probability of a profitable trade
        if price < row['VWAP'] - threshold * atr and (prev['EMA9_DIFF'] * row['EMA9_DIFF'] < 0) and row[
            'ROC_VWAP'] > 0:
            return True, 'buy'
        elif price > row['VWAP'] + threshold * atr and (prev['EMA9_DIFF'] * row['EMA9_DIFF'] < 0) and row[
            'ROC_VWAP'] < 0:
            return True, 'sell'

        return False, None

    def exit_signal(self, current_position):
       #strategy uses stop loss and take profit. This should be handles in the open and close position logic
        pass



def mean_reversion(df, threshold, window, rr, atr_mult=0.5, max_hold=10, slippage=0.0005):
    window = int(window)
    df = df.copy()
    df['VWAP'] = (df['Close'] * df['Volume']).rolling(window).sum() / df['Volume'].rolling(window).sum()
    df['ATR'] = (df['Close'] - df['Close'].shift(1)).abs().rolling(window).mean()
    df['ROC_VWAP'] = df['VWAP'].pct_change(5)
    df['Position'] = 0
    df['Target'] = 0
    df['EMA9'] = df['Close'].ewm(span=7, adjust=False).mean()
    df['EMA9_DIFF'] = df['EMA9'].diff()

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
        prev = df.iloc[i - 1]
        price = row['Close']

        atr = row['ATR']

        # Entry
        if in_position == 0:
            if price < row['VWAP'] - threshold * atr and (prev['EMA9_DIFF'] * row['EMA9_DIFF'] < 0) and row[
                'ROC_VWAP'] > 0:
                in_position = 1
                entry_price = price * (1 + slippage)
                entry_index = df.index[i]
                entry_i = i
            elif price > row['VWAP'] + threshold * atr and (prev['EMA9_DIFF'] * row['EMA9_DIFF'] < 0) and row[
                'ROC_VWAP'] < 0:
                in_position = -1
                entry_price = price * (1 - slippage)
                entry_index = df.index[i]
                entry_i = i

        # Long position
        elif in_position == 1:
            if price >= entry_price + rr * atr or price <= entry_price - atr_mult * atr or (i - entry_i) >= max_hold:
                profit = price - entry_price
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0
                cooldown = 2

        # Short position
        elif in_position == -1:
            if price <= entry_price - rr * atr or price >= entry_price + atr_mult * atr or (i - entry_i) >= max_hold:
                profit = entry_price - price
                df.at[entry_index, 'Target'] = int(profit > 0)
                in_position = 0
                cooldown = 2

        df.iloc[i, df.columns.get_loc('Position')] = in_position

    df['Target'] = df['Target'].fillna(0).astype(int)
    return df.dropna()