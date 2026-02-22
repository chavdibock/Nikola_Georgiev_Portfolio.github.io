import threading
import time
import queue
import pandas as pd
import numpy as np
from crud import crud
from db.db import get_db
from sqlalchemy.orm import Session
from utils import utils as utl
from core.config import settings
import requests

# Initialize a thread-safe queue
stock_queue = queue.Queue()


# Ensure a new database session for each thread
def get_db_session():
    return next(get_db())  # Returns a new session from the generator


# Function to process and add items from queue to DB
def add_queue_to_db():
    """Processes and inserts items from the queue into the DB."""
    while not stock_queue.empty():
        stock = stock_queue.get()

        db: Session = get_db_session()
        try:
            print(f"Inserting stock {stock['symbol']} into the DB.")
            crud.add_stock(
                db,
                stock['symbol'] if pd.notna(stock['symbol']) else "N/A",
                stock['price'] if np.isfinite(stock['price']) else 0,
                stock['vwap'] if np.isfinite(stock['vwap']) else 0,
                stock['macd'] if np.isfinite(stock['macd']) else 0,
                stock['weighted_pct_sum'] if np.isfinite(stock['weighted_pct_sum']) else 0,
                stock['macd_condition'] if pd.notna(stock['macd_condition']) else "N/A",
                stock['ma_calculation'] if np.isfinite(stock['ma_calculation']) else 0,
                stock['stop_loss'] if np.isfinite(stock['stop_loss']) else 0
            )
        except Exception as e:
            print(f"Error inserting stock {stock['symbol']}: {e}")
            db.rollback()
        finally:
            db.close()


# Function to process stock data and add to queue
def process_stock(stock):
    start_time = time.time()

    period = settings.PERIOD  # PERIOD
    bar = settings.BARS_SIZE  # BAR_SISE
    market_data = utl.historicalData(stock['con_id'], period, bar)
    if market_data["error"] != "VALID":
        return

    vwap, weighted_pct_sum = utl.calculate_vwap(market_data, 120)
    ma_calculation = utl.calculate_moving_average(market_data, 60)
    macd, macd_condition = utl.calculate_adaptive_macd(market_data)
    stop_loss = utl.get_stop_loss(market_data, 20)

    ohlcv = pd.DataFrame(market_data['price_history']['data'])
    ohlcv[['h', 'l', 'c', 'v']] = ohlcv[['h', 'l', 'c', 'v']].apply(pd.to_numeric, errors='coerce')
    ohlcv.dropna(inplace=True)

    price = ohlcv['c'].iloc[-1]


    # Add stock to queue instead of inserting directly
    print(f"Processing stock {stock['conidex']}")
    stock_queue.put({
        'symbol': market_data['contract']['ticker'],
        'price': price,
        'vwap': vwap,
        'macd': macd,
        'weighted_pct_sum': weighted_pct_sum,
        'macd_condition': macd_condition,
        'ma_calculation': ma_calculation,
        'stop_loss': stop_loss
    })

    elapsed_time = time.time() - start_time
    print(f"Processed {stock['con_id']} in {elapsed_time:.4f} seconds")


# Function to run stock processing with a timeout **concurrently**
def screener():
    stocks = utl.get_scanner_stocks()
    threads = []
    trh_db = []

    for stock in stocks:
        thread = threading.Thread(target=process_stock, args=(stock,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # Wait for all threads to complete

    # Background thread for DB insertion
    db = get_db_session()
    crud.add_stocks(db, stock_queue)
    return True


# Main loop
if __name__ == '__main__':
    crud.manage_settings(db=next(get_db()))
    while True:
        if utl.is_market_open():
            try:
                # Open a new session to truncate the table
                crud.truncate_table(table="stocks")

                # Run screener
                print("Running screener to insert stocks...")
                screener()

                print("Waiting for 60 seconds before next cycle.")
                time.sleep(60)  # Adjust timing as neededf
                # db_session = get_db_session()
                # crud.truncate_table(db=db_session, table="stocks")
            except Exception as e:
                print(f"Error during main loop execution: {e}")
        else:
            time.sleep(60)

# utl.test_hist_data()
