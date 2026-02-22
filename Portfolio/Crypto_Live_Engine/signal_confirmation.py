import asyncio
import websockets
import json
import numpy as np
from collections import deque
import time
import sys

class BinanceOrderFlow:
    def __init__(self, symbol="btcusdt", avg_15m_volume=100, direction='buy', position_confirmed_event=None):
        self.symbol = symbol.lower()
        self.avg_15m_volume = avg_15m_volume
        self.direction = direction.lower()
        self.position_confirmed_event = position_confirmed_event or asyncio.Event()

        self.depth_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@depth10@100ms"
        self.trade_url = f"wss://stream.binance.com:9443/ws/{self.symbol}@trade"

        self.order_book = {"bids": {}, "asks": {}}
        self.tape = deque(maxlen=5000)
        self.volume_history = deque(maxlen=15)

        self.depth_ready = asyncio.Event()
        self.window_seconds = 60
        self.signal_frequency = 5
        self.N_levels = 5

    async def start(self):
        await asyncio.gather(
            self.run_depth(),
            self.run_trades(),
            self.analyze_orderflow()
        )

    async def run_depth(self):
        while not self.position_confirmed_event.is_set():
            try:
                async with websockets.connect(self.depth_url, ping_interval=20, ping_timeout=10) as ws:
                    async for message in ws:
                        if self.position_confirmed_event.is_set():
                            return
                        data = json.loads(message)
                        bids = {float(p): float(q) for p, q in data['bids']}
                        asks = {float(p): float(q) for p, q in data['asks']}
                        self.order_book = {"bids": bids, "asks": asks}
                        self.depth_ready.set()
            except Exception as e:
                print(f"[{self.symbol}] Depth connection error: {e}, retrying in 5s")
                await asyncio.sleep(5)

    async def run_trades(self):
        while not self.position_confirmed_event.is_set():
            try:
                async with websockets.connect(self.trade_url, ping_interval=20, ping_timeout=10) as ws:
                    async for message in ws:
                        if self.position_confirmed_event.is_set():
                            return
                        data = json.loads(message)
                        price = float(data['p'])
                        qty = float(data['q'])
                        ts = time.time()

                        best_bid = max(self.order_book['bids'].keys(), default=0)
                        best_ask = min(self.order_book['asks'].keys(), default=0)

                        if price >= best_ask:
                            side = 'buy'
                        elif price <= best_bid:
                            side = 'sell'
                        else:
                            side = 'unknown'

                        self.tape.append({'price': price, 'qty': qty, 'side': side, 'ts': ts})
            except Exception as e:
                print(f"[{self.symbol}] Trade connection error: {e}, retrying in 5s")
                await asyncio.sleep(5)

    async def analyze_orderflow(self):
        await self.depth_ready.wait()

        start_time = time.time()
        max_duration = 15 * 60

        while time.time() - start_time < max_duration:
            if self.position_confirmed_event.is_set():
                print(f"[{self.symbol}] Cancelled due to confirmation elsewhere.")
                return

            await asyncio.sleep(self.signal_frequency)

            try:
                now = time.time()
                trades_window = [t for t in self.tape if now - t['ts'] <= self.window_seconds]
                if not trades_window:
                    continue

                buy_qty = sum(t['qty'] for t in trades_window if t['side'] == 'buy')
                sell_qty = sum(t['qty'] for t in trades_window if t['side'] == 'sell')
                total_volume = buy_qty + sell_qty

                self.volume_history.append(total_volume)

                print(
                    f"[{self.symbol.upper()}] 1-min Vol: {total_volume:.1f} (avg {self.avg_15m_volume:.1f}) | "
                    f"Buy: {buy_qty:.1f} | Sell: {sell_qty:.1f}"
                )

                if total_volume > 1.5 * self.avg_15m_volume:
                    if self.direction == 'buy' and buy_qty > 2 * sell_qty:
                        print(f"==>  CONFIRMED BUY SIGNAL on {self.symbol.upper()}")
                        self.position_confirmed_event.set()
                        return
                    elif self.direction == 'sell' and sell_qty > 2 * buy_qty:
                        print(f"==>  CONFIRMED SELL SIGNAL on {self.symbol.upper()}")
                        self.position_confirmed_event.set()
                        return

            except Exception as e:
                print(f"[{self.symbol}] Analysis error: {e}")

        print(f"[{self.symbol}] Order flow analysis completed (15-minute limit reached).")
