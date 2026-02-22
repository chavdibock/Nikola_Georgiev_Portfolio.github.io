import time

import requests
from sqlalchemy.orm import Session

from core.config import settings
from crud import crud
from db.db import get_db
from utils import utils as utl


def get_status():
    try:
        auth_req = requests.get(url=f"{settings.ibkr_client}/iserver/auth/status", verify=False)
        if auth_req.status_code == 200 and auth_req.json().get("authenticated", False):
            return True
        else:
            return False
    except Exception as e:
        print(e)


def in_position(con_id, acc_id):
    # print(utl.check_if_in_pos_count(con_id=con_id, acc_id=acc_id))
    if utl.check_if_in_pos(con_id=con_id, acc_id=acc_id):
        return True
    return False


def strategy(db: Session, prob_stocks):
    # Query stocks from the last minute where vwap_calculation > 0
    try:

        stocks = crud.get_strategy_stocks(db)
        if stocks:
            for i in stocks:
                if i.symbol not in prob_stocks:
                    return i
        else:
            return None
    except Exception as e:
        print(e)


def get_db_session():
    return next(get_db())


if __name__ == "__main__":

    # pod = 0  # max of 3 positions
    utl.supress(None)
    stocks_with_problem = []
    while True:
        if utl.is_market_open():
            stock = strategy(db=get_db_session(), prob_stocks=stocks_with_problem)
            if stock is not None:
                con_id = utl.contractSearch(stock.symbol, "STK")
                print(con_id, "", stock.symbol)
                if in_position(con_id=con_id, acc_id=settings.IBKR_USER) is True:
                    atr = float(stock.stop_loss)
                    print("Opening trade")
                    ord_res = utl.open_order(con_id=con_id, acc_id=settings.IBKR_USER, atr=atr)
                    if ord_res is False:
                        stocks_with_problem.append(stock.symbol)
                        print("##################")
                        print("##################")
                        print("Failed to open order with: ", stock.symbol)
                        print("##################")
                        print("##################")
            else:
                print("There was no stock")
            time.sleep(60)
