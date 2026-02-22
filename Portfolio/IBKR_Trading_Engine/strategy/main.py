import datetime
import time
import requests
from core.config import settings
from utils import utils as utl
import datetime
from core.config import settings
import pytz


def get_status():
    try:
        auth_req = requests.get(url=f"{settings.ibkr_client}iserver/auth/status", verify=False)
        if auth_req.status_code == 200 and auth_req.json().get("authenticated", False):
            return True
        else:
            return False
    except Exception as e:
        print(e)


def ross_strategy():
    traded_stocks = []
    trading_stock = 1
    acc_id = settings.IBKR_USER
    utl.supress(None)
    while True:
        try:
            ny_tz = pytz.timezone("America/New_York")
            now = datetime.datetime.now(ny_tz).time()

            if now == datetime.time(8, 0):
                traded_stocks = []

            if utl.is_market_open():
                print(f"This is the client: {settings.ibkr_client}")
                in_pos = utl.check_if_in_pos(con_id=trading_stock, acc_id=acc_id)

                print("Currently in pos: ", in_pos)
                if in_pos is False:
                    stocks = utl.adjust_scanner_data(min_prc_change=10)
                    for i in stocks:
                        if i["con_id"] not in traded_stocks:
                            print("Starting to trade: ", i["con_id"])
                            traded_stocks.append(i["con_id"])
                            trading_stock = i["con_id"]
                            ord_status = utl.open_order(con_id=i["con_id"], acc_id=acc_id, )
                            if ord_status is True:
                                break

        except Exception as e:
            print("##################################")
            print("##################################")
            print("############# ERROR #############")
            print(e)
            print("##################################")
            print("##################################")

        time.sleep(60 * 2)


if __name__ == "__main__":
    while True:
        status = get_status()
        if status is True:
            break
        time.sleep(5)

    ross_strategy()
