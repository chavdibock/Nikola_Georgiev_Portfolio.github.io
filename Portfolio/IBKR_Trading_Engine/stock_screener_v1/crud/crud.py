from core.config import settings
from models import models
from sqlalchemy.orm import Session


def get_all_stocks(db: Session):
    return db.query(models.Stock).all()


def add_stock(db: Session, symbol, price, vwap, macd):
    stocks = db.add(
        models.Stock(
            symbol=symbol,
            price=price,
            vwap=vwap,
            macd=macd,
        )
    )
    db.commit()


if __name__ == '__main__':
    pass
