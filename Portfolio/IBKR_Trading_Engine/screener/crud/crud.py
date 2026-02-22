import numpy as np
import pandas as pd
from core.config import settings
from models import models
from sqlalchemy.orm import Session
from sqlalchemy import text
from db.db import get_db


def get_all_stocks(db: Session):
    stocks = db.query(models.Stock).all()

    # Print results
    for stock in stocks:
        print(stock.vwap)


def add_stocks(db, stock_queue):
    stocks_to_insert = []  # List to hold stocks to insert in bulk

    while not stock_queue.empty():
        stock = stock_queue.get()

        # Prepare data for bulk insert (dictionary format)
        stock_data = {
            'symbol': stock['symbol'] if pd.notna(stock['symbol']) else "N/A",
            'price': stock['price'] if np.isfinite(stock['price']) else 0,
            'vwap': stock['vwap'] if np.isfinite(stock['vwap']) else 0,
            'macd': stock['macd'] if np.isfinite(stock['macd']) else 0,
            'weighted_pct_sum': stock['weighted_pct_sum'] if np.isfinite(stock['weighted_pct_sum']) else 0,
            'macd_condition': stock['macd_condition'] if pd.notna(stock['macd_condition']) else "N/A",
            'ma_calculation': stock['ma_calculation'] if np.isfinite(stock['ma_calculation']) else 0,
            'stop_loss': stock['stop_loss'] if np.isfinite(stock['stop_loss']) else 0,
            'scr_id': settings.SCR_ID
        }

        stocks_to_insert.append(stock_data)  # Add to list for bulk insert

    # Insert all stocks at once if there are stocks to insert
    if stocks_to_insert:
        try:
            print(f"Inserting {len(stocks_to_insert)} stocks into the DB.")
            # Bulk insert all stocks at once
            db.bulk_insert_mappings(models.Stock, stocks_to_insert)
            db.commit()  # Commit the transaction
        except Exception as e:
            print(f"Error during bulk insert: {e}")
            db.rollback()  # Rollback in case of error
        finally:
            db.close()


def truncate_table(table: str):
    db = next(get_db())
    stm = f"delete from {table} where id >=1"
    # print(stm)
    db.execute(text(stm))
    db.commit()
    db.close()
    print("Truncating table")


def manage_settings(db: Session):
    existing = db.query(models.ScreenerSettings).filter_by(scr_id=settings.SCR_ID).first()

    if not existing:
        new_scr_setting = models.ScreenerSettings(
            scr_id=settings.SCR_ID,
            period=settings.PERIOD,
            bars_size=settings.BARS_SIZE,
            calc_vwap_window=float(settings.CALC_VWAP_WINDOW),
            moving_avg_window=float(settings.MOVING_AVG_WINDOW),
            macd_len=float(settings.MACD_LEN),
            macd_fast=float(settings.MACD_FAST),
            macd_slow=float(settings.MACD_SLOW),
            calc_st_loss=float(settings.CALC_ST_LOSS)
        )
        db.add(new_scr_setting)
        try:
            db.commit()
            print("New record inserted.")
        except Exception as e:
            db.rollback()
            print("Record insertion failed due to integrity error (possibly duplicate).")
            print(e)
    else:
        print("Record already exists. Doing nothing.")


if __name__ == '__main__':
    pass
