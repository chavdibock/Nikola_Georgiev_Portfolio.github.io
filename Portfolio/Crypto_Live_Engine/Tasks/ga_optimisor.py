import numpy as np
import pandas as pd
import requests
from scipy.stats import stats
import BinanceBot.Models.Coins as Coins
from BinanceBot.Helpers.db_crud import MySQLDatabase

#This script will be only concerned with optimising strategy parameters on last 3 days data.
#It will loop through all of the coins once every 2-5 days and check the best startegy

class Genome:
    def __init__(self, strategy_type, params):
        self.strategy_type = strategy_type
        self.params = params
        self.fitness = None

    def mutate(self, mutation_rate=0.1):
        for param in self.params:
            if np.random.rand() < mutation_rate:
                mutation_scale = 0.1 if isinstance(self.params[param], float) else 5
                mutated_value = self.params[param] + np.random.normal(0, mutation_scale)

                if param in ['window', 'ma_window', 'vwap_window', 'max_hold']:
                    mutated_value = max(1, int(mutated_value))  # allow 1+ bars hold
                else:
                    mutated_value = max(0.01, mutated_value)

                self.params[param] = mutated_value


class Population:
    def __init__(self, size, genome_factories, elite_size):
        self.individuals = []
        self.elite_size = elite_size
        for factory in genome_factories:
            self.individuals.extend([factory() for _ in range(size // len(genome_factories))])

    def evaluate(self, backtester, data):
        for individual in self.individuals:
            try:
                df, pnl, sharpe = backtester.run(individual, data)
                individual.fitness = sharpe
            except Exception as e:
                print(f"Error evaluating genome {individual.strategy_type} {individual.params}: {e}")
                individual.fitness = -np.inf

    def select_parents(self, num_parents=10):
        self.individuals.sort(key=lambda x: x.fitness if x.fitness is not None else -np.inf, reverse=True)
        return self.individuals[:num_parents]

    def crossover(self, parent1, parent2):
        if parent1.strategy_type != parent2.strategy_type:
            return parent1
        child_params = {}
        for param in parent1.params:
            if param in parent2.params:
                child_params[param] = parent1.params[param] if np.random.rand() < 0.5 else parent2.params[param]
            else:
                child_params[param] = parent1.params[param]
        return Genome(parent1.strategy_type, child_params)

    def generate_new_population(self, parents, mutation_rate):
        # Sort population by fitness in descending order
        self.individuals.sort(key=lambda x: x.fitness if x.fitness is not None else -np.inf, reverse=True)

        # Elites: top N best individuals
        elites = [Genome(ind.strategy_type, ind.params.copy()) for ind in self.individuals[:self.elite_size]]

        new_individuals = elites.copy()
        while len(new_individuals) < len(self.individuals):
            p1, p2 = np.random.choice(parents, 2, replace=False)
            child = self.crossover(p1, p2)
            child.mutate(mutation_rate)
            new_individuals.append(child)

        self.individuals = new_individuals


class Backtester:
    def run(self, genome, data):
        df = data.copy()
        params = genome.params

        if genome.strategy_type == 'mean_reversion':
            df = mean_reversion(df, params['threshold'], params['window'], params['rr'],
                                params.get('atr_mult', 0.5), params.get('max_hold', 10))
        elif genome.strategy_type == 'breakout':
            df = breakout_strategy(df, params['z_thresh'], params['ma_window'], params['vwap_window'], params['rr'],
                                   params.get('atr_mult', 0.5), params.get('max_hold', 10))

        df['returns'] = df['Close'].pct_change()
        df['Strategy Returns'] = df['Position'].shift(1) * df['returns']
        df['Equity Curve'] = (1 + df['Strategy Returns']).cumprod()

        pnl = df['Strategy Returns'].sum()
        sharpe = df['Strategy Returns'].mean() / (df['Strategy Returns'].std() + 1e-9)
        return df, pnl, sharpe


# Genome Factories
def mean_reversion_genome_factory():
    return Genome('mean_reversion', {
        'threshold': np.random.uniform(0, 5),
        'window': np.random.randint(30, 120),
        'rr': np.random.uniform(1, 3.0),
        'atr_mult': np.random.uniform(0.3, 3),
        'max_hold': np.random.randint(3, 20)
    })


def breakout_genome_factory():
    return Genome('breakout', {
        'z_thresh': np.random.uniform(-2, 2.0),
        'ma_window': np.random.randint(30, 120),
        'vwap_window': np.random.randint(30, 100),
        'rr': np.random.uniform(1, 3.0),
        'atr_mult': np.random.uniform(1, 3),
        'max_hold': np.random.randint(5, 20)
    })


# Binance Data Fetcher
def load_data(symbol, limit=672):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": '15m', "limit": limit}
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    cols = ['openTime', 'open', 'high', 'low', 'close', 'volume',
            'closeTime', 'quoteAssetVolume', 'tradeCount',
            'takerVolume', 'takerAmount', 'ignore']
    df = pd.DataFrame(data, columns=cols)
    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
    df.set_index('openTime', inplace=True)
    df['Close'] = df['close'].astype(float)
    df['Volume'] = df['volume'].astype(float)
    return df[['Close', 'Volume']]


def mean_reversion(df, threshold, window, rr, atr_mult=0.5, max_hold=10, slippage=0.0005):
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


# Breakout Strategy

def breakout_strategy(df, z_thresh, ma_window, vwap_window, rr, atr_mult=0.5, max_hold=10, slippage=0.0005):
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


# GA Engine
class GAEngine:
    def __init__(self, population_size=80, generations=30, mutation_rate=0.2):
        self.population = Population(population_size, [mean_reversion_genome_factory, breakout_genome_factory], 10)
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.backtester = Backtester()

    def evolve(self, data):
        for _ in range(self.generations):
            self.population.evaluate(self.backtester, data)
            parents = self.population.select_parents()
            self.population.generate_new_population(parents, self.mutation_rate)
        champion = max(self.population.individuals, key=lambda x: x.fitness if x.fitness is not None else -np.inf)
        return champion


def test_strategy_significance(returns, alpha=0.05):
    returns = returns.dropna()
    t_stat, p_value_two_sided = stats.ttest_1samp(returns, popmean=0)

    # Convert to one-sided p-value (H1: mean > 0)
    if t_stat > 0:
        p_value_one_sided = p_value_two_sided / 2
    else:
        p_value_one_sided = 1 - (p_value_two_sided / 2)

    if p_value_one_sided < alpha:
        return True
    else:
        return False


def ga_optimise():
    db = MySQLDatabase()
    coins = Coins.CoinRepository(db)
    all_coins = coins.get_all_coins()
    for symbol in all_coins:
        symbol = symbol.get("symbol")
        print(symbol)

        data = load_data(symbol)
        ga = GAEngine()
        best_strategy = ga.evolve(data)

        backtester = Backtester()
        result_df, total_return, sharpe_ratio = backtester.run(best_strategy, data)

        clean_params = {k: float(v) for k, v in best_strategy.params.items()}
        total_return = float(total_return)

        # Now update safely

        if test_strategy_significance(result_df['Strategy Returns']):
            info = coins.update_strategy_info_by_symbol(
                symbol,
                best_strategy.strategy_type,
                clean_params,
                True,
                total_return
            )
        else:
            info = coins.update_strategy_info_by_symbol(symbol, None, None, False, None)
            return [], []



if __name__ == "__main__":
    ga_optimise()



    """
    data = load_data('BTCUSDT')
    ga = GAEngine()
    best_strategy = ga.evolve(data)

    print(f"Champion strategy: {best_strategy.strategy_type}")
    print(f"Optimal parameters: {best_strategy.params}")

    backtester = Backtester()
    result_df, total_return, sharpe_ratio = backtester.run(best_strategy, data)

    result_df['Equity Curve'].plot(title='Equity Curve of Best Strategy', figsize=(10, 6))


    print(f"Total Return: {total_return:.4f}")
    print(f"Sharpe Ratio: {sharpe_ratio:.4f}")

   
    """
    """
       Champion strategy: breakout
       Optimal parameters: {'z_thresh': 0.08973809928381112, 'ma_window': 61, 'vwap_window': 102, 'rr': 2.439882162852047, 'atr_mult': 1.228965142875869, 'max_hold': 7}
       Total Return: 0.1060
       Sharpe Ratio: 0.1282
       """