import asyncio
import json
from datetime import datetime

import pandas as pd
import requests

from FreqTrade.Helpers.db_crud import MySQLDatabase
from FreqTrade.Strategies import MeanReversion as mr
from FreqTrade.Strategies import Breakout as br
import FreqTrade.signal_confirmation as signal_confirmation
import FreqTrade.Models.Coins as Coins


def get_latest_candles_web(symbol, limit=200):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": "15m", "limit": limit}

    response = requests.get(url, params=params)
    response.raise_for_status()  # cleaner error handling

    data = response.json()
    df = pd.DataFrame(data, columns=[
        'openTime', 'open', 'high', 'low', 'close', 'volume',
        'closeTime', 'quoteAssetVolume', 'tradeCount',
        'takerVolume', 'takerAmount', 'ignore'
    ])
    df['openTime'] = pd.to_datetime(df['openTime'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)

    df.set_index('openTime', inplace=True)
    return df[['close', 'volume']].rename(columns={'close': 'Close', 'volume': 'Volume'})


def load_strategy(symbol, df, strategy_name, best_params):
    if strategy_name == "mean_reversion" or strategy_name == "mean reversion":
        return mr.MeanReversion(symbol, df, best_params)
    elif strategy_name == "breakout":
        return br.Breakout(symbol, df, best_params)
    return None


async def check_exit_conditions(symbol, df, strategy_name, best_params, position_side):
    strategy = load_strategy(symbol, df, strategy_name, best_params)
    if strategy and strategy.exit_signal(position_side):
        # TODO: Implement sending exit order, updating DB, etc.
        print(f"Exit signal triggered for {symbol}")


async def check_entry_conditions(symbol, df, strategy_name, best_params):
    strategy = load_strategy(symbol, df, strategy_name, best_params)
    if strategy:
        should_enter, direction = strategy.entry_signal()
        if should_enter and direction:
            avg_15m_volume = df['Volume'].ewm(span=15, adjust=False).mean().iloc[-1]
            avg_1m_volume = avg_15m_volume / 15

            bot = signal_confirmation.BinanceOrderFlow(
                symbol=symbol,
                avg_15m_volume=avg_1m_volume,
                direction=direction
            )
            await bot.start()



async def run_parallel_orderflows(entry_signals):
    position_confirmed = asyncio.Event()
    tasks = []

    for signal in entry_signals:
        bot = signal_confirmation.BinanceOrderFlow(
            symbol=signal['symbol'],
            avg_15m_volume=signal['avg_15m_volume'],
            direction=signal['direction'],
            position_confirmed_event=position_confirmed
        )
        task = asyncio.create_task(bot.start())
        tasks.append(task)

    await position_confirmed.wait()
    print("✅ Position confirmed — cancelling all other bots...")

    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print("Cancelled order flow task.")



async def run_screener():
    print("\n[ Screener Started at", datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), "]")

    db = MySQLDatabase()
    coins_repo = Coins.CoinRepository(db)
    all_coins = coins_repo.get_all_coins()

    exit_tasks = []
    entry_signals = []

    for coin in all_coins:
        symbol = coin.get("symbol")
        if not coin.get("is_active"):
            continue

        try:
            df = get_latest_candles_web(symbol)
            if df.empty:
                continue

            strategy_name = coin.get("strategy")
            best_params_json = coin.get("best_params")
            best_params = json.loads(best_params_json) if best_params_json else {}

            if coin.get("in_position"):
                exit_tasks.append(
                    check_exit_conditions(symbol, df, strategy_name, best_params, coin.get("position_side"))
                )
            else:
                strategy = load_strategy(symbol, df, strategy_name, best_params)
                if strategy:
                    should_enter, direction = strategy.entry_signal()
                    if should_enter and direction:
                        avg_15m_volume = df['Volume'].ewm(span=15, adjust=False).mean().iloc[-1]
                        avg_1m_volume = avg_15m_volume / 15
                        entry_signals.append({
                            'symbol': symbol,
                            'avg_15m_volume': avg_1m_volume,
                            'direction': direction
                        })

        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    # Run exit checks concurrently
    if exit_tasks:
        await asyncio.gather(*exit_tasks)

    # Run entry signals in parallel with cancellation logic
    if entry_signals:
        await run_parallel_orderflows(entry_signals)



async def scheduler():
    while True:
        now = datetime.utcnow()
        if now.minute % 1 == 0:
            await run_screener()
            await asyncio.sleep(60)  # avoid rerun in the same minute
        else:
            await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(scheduler())
