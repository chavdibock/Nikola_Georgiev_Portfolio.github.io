from datetime import datetime, timedelta
from sqlalchemy import text, select
from core.config import settings
from models import models
from sqlalchemy.orm import Session
import time


def get_all_stocks(db: Session):
    stocks = db.query(models.Stock).all()

    return stocks


def get_strategy_stocks(db: Session):
    # two_minutes_ago = datetime.utcnow() - timedelta(minutes=2)
    MAX_RETRIES = 10
    RETRY_DELAY = 1
    # this is a test comment
    for attempt in range(MAX_RETRIES):
        try:
            stm = (
                select(models.Stock)
                .where(
                    models.Stock.macd_condition == 1,
                    models.Stock.ma_calculation >= 0.04
                )
                .order_by(models.Stock.ma_calculation.desc())
            )

            stocks = db.scalars(stm).all()
            stocks_list = [stock for stock in stocks if stock.price >= stock.vwap]

            if stocks_list:  # Check if the list is non-empty
                return stocks_list
            else:
                print(f"Attempt {attempt + 1}: No qualifying stocks found.")

        except Exception as e:
            print(f"Attempt {attempt + 1} failed with error: {e}")

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY)

        # After all retries
    print("Max retries reached. No stocks found.")
    return []


def add_stock(db: Session, symbol, price, vwap, macd, vwap_calculation, macd_condition, weighted_ma_sum, stop_loss):
    db.add(
        models.Stock(
            symbol=symbol,
            price=float(price),
            vwap=float(vwap),
            macd=float(macd),
            vwap_calculation=float(vwap_calculation),
            macd_condition=macd_condition,
            ma_calculation=weighted_ma_sum,
            stop_loss=stop_loss
        )
    )
    db.commit()


if __name__ == '__main__':
    pass
