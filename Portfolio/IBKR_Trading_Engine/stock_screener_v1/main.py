import time

import pandas as pd

from crud import crud
from db.db import get_db
from sqlalchemy.orm import Session

from crud import crud
from utils import utils as utl

db: Session = next(get_db())

if __name__ == '__main__':
    # stocks = utl.get_scanner_stocks()
    # print(utl.get_all_snapshots(stocks=stocks))
    # for i in stocks:
    #    print(utl.get_snapshot(i["con_id"], ["7762", "7282", "86", "84", "82", "83"]))
    stk = utl.screener()

    for i in stk:
        print(i)
