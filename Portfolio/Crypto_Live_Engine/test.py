from signal_confirmation import BinanceOrderFlow
import asyncio

async def run_multiple_orderflows(entry_signals):
    # entry_signals is a list of dicts like:
    # [{'symbol': 'BTCUSDT', 'volume': 1234, 'direction': 'buy'}, ...]

    position_confirmed = asyncio.Event()
    tasks = []

    for signal in entry_signals:
        bot = BinanceOrderFlow(
            symbol=signal['symbol'],
            avg_15m_volume=signal['volume'],
            direction=signal['direction'],
            position_confirmed_event=position_confirmed
        )
        tasks.append(asyncio.create_task(bot.start()))

    await position_confirmed.wait()

    print("✅ Position confirmed — cancelling all other bots...")

    for task in tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print("Cancelled task cleanly.")

    print("All bots stopped after confirmation.")


entry_signals = [
    {'symbol': 'BTCUSDT', 'volume': 1, 'direction': 'buy'},
   # {'symbol': 'ETHUSDT', 'volume': 1, 'direction': 'buy'},
    #{'symbol': 'SOLUSDT', 'volume': 1, 'direction': 'sell'},
]

asyncio.run(run_multiple_orderflows(entry_signals))