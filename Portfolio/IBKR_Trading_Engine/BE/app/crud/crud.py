from core.config import settings
from models import models
from sqlalchemy.orm import Session


def get_all_stocks(db: Session):
    stocks = db.query(models.Stock).all()
    res = []
    for i in stocks:
        res.append(
            {
                "con_id": i.con_id,
                "ticker": i.ticker,
                "amount": i.amount,
                "screener_id": i.screener_id,
                "screener_weight": i.screener_weight

            }
        )

    return res


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
