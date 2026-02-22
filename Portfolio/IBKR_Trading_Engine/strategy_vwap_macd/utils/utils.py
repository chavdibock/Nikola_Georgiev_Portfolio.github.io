import json
import threading
import time

import pytz
import websocket
import datetime
import requests
import csv
from tradingview_screener import Query, Column  # 'BINANCE:BTCUSDT'
import numpy as np
from core.config import settings


# DUH196417
def get_account_cash(acc_id):
    base_url = settings.IBKR_BASE
    endpoint = f"portfolio/{acc_id}/summary"
    print(base_url + endpoint)
    try:

        acc_req = requests.get(url=base_url + endpoint, verify=False)
        acc_req_json = json.dumps(acc_req.json(), indent=2)
        # print(acc_req_json)
        cash = acc_req.json()["totalcashvalue"]["amount"]
        # print(cash)
        return float(cash)

    except Exception as e:
        print(e)


def round_price(number, point):
    value_str = str(number)

    try:
        index = value_str.find('.')
        if index == -1:
            return number
        else:
            return float(value_str[:index + point])
    except:
        return number


def get_snapshot(con_id, fields):
    base_url = settings.IBKR_BASE
    endpoint = "iserver/marketdata/snapshot"
    if fields is None:
        fields = ["82", "7762", "7282", "86", "84"]
    scanner_fields = ""
    scanner_fields = ",".join(fields)

    # print(con_id)
    conid = f"conids={con_id}"
    fields_req = f"fields={scanner_fields}"
    params = "&".join([conid, fields_req])
    start_time = time.time()
    timeout = 5
    res = {"status": "Invalid"}
    while time.time() - start_time < timeout:
        try:
            request_url = "".join([base_url, endpoint, "?", params])
            md_req = requests.get(url=request_url, verify=False)
            md_req_js = md_req.json()
            # print("This is the response")
            # print(md_req_js[0])

            res["ask"] = float(md_req_js[0]["86"])
            res["bid"] = float(md_req_js[0]["84"])
            res["con_id"] = con_id
            res["status"] = "Valid"
        # md_json = json.dumps(md_req.json(), indent=2)
        # print(md_req)
        # print(md_json)
        except Exception as e:
            # print(md_req.json())
            print(e)
    time.sleep(1)
    return res


def is_market_open():
    # Get current time in New York timezone
    ny_tz = pytz.timezone("America/New_York")
    now = datetime.datetime.now(ny_tz).time()  # Extract only the time part

    # Market open time: 9:30 AM, Market close time: 4:00 PM
    market_open = datetime.time(9, 30)
    market_close = datetime.time(16, 0)

    return market_open <= now <= market_close


def open_order(con_id, acc_id, atr):
    try:
        base_url = settings.IBKR_BASE
        endpoint = f"iserver/account/{settings.IBKR_USER}/orders"
        time.sleep(0.5)
        prc = get_snapshot(con_id=con_id, fields=None)
        print(con_id)
        print(prc)
        time.sleep(1)
        available_cash = get_account_cash(acc_id)
        time.sleep(1)
        qty = int((0.2 * available_cash) / prc["ask"])

        prf_price = round_price(prc["ask"] * (1 + settings.TAKE_PROFIT), 3)
        st_price = round_price(prc["ask"] * (1 - settings.STOP_LOSS), 3)

        risk_per_trade = 0.03 * available_cash  # 3% of available cash
        stop_loss_per_unit = settings.STOP_LOSS * atr

        qty = int(risk_per_trade / stop_loss_per_unit)

        if qty > int((0.2 * available_cash) / prc["ask"]):
            qty = int((0.2 * available_cash) / prc["ask"])
        if qty > 24500:
            qty = 20000

        if settings.trading_env != "PAPER":
            qty = 1
        # print(st_price)
        mrk_ord = f"{datetime.datetime.now().timestamp()}_{settings.TAKE_PROFIT}_{settings.STOP_LOSS}_MRK"

        json_body = {
            "orders": [
                {
                    "cOID": mrk_ord,
                    "conid": int(con_id),
                    "orderType": "MKT",
                    "side": "BUY",
                    "tif": "GTC",
                    "quantity": qty
                }
                ,
                {
                    "parentId": mrk_ord,
                    "cOID": f"{mrk_ord}_TP_LIMIT",
                    "conid": int(con_id),
                    "orderType": "LMT",
                    "price": prf_price,
                    "side": "SELL",
                    "tif": "GTC",
                    "quantity": qty
                },
                {
                    "parentId": mrk_ord,
                    "cOID": f"{mrk_ord}_ST_LIMIT",
                    "conid": int(con_id),
                    "orderType": "STP",
                    "price": st_price,
                    "side": "SELL",
                    "tif": "GTC",
                    "quantity": qty
                }
            ]
        }
        print("This is the body")
        print(json_body)

        order_req = requests.post(url=base_url + endpoint, verify=False, json=json_body)
        order_json = order_req.json()
        pr_order_json = json.dumps(order_json, indent=2)
        print(order_req.status_code)
        print(pr_order_json)
        if "error" in order_json:
            return False
        elif "isSuppressed" in order_json:
            spr_id = order_json[2]["messageIds"][0]
            print(f"Unsuppressed message: {spr_id}")
            supress(spr_id)
            return False
        else:
            return True
    except Exception as e:
        print("##################")
        print("##################")
        print("Error Opening Trade")
        print(e)
        print("##################")
        print("##################")
        return False


def contractSearch(symbol, type):
    base_url = settings.IBKR_BASE
    endpoint = "iserver/secdef/search"
    json_body = {"symbol": symbol, "type": type, "name": True}
    try:

        contract_req = requests.post(url=base_url + endpoint, verify=False, json=json_body).json()
        # return contract_req

        for i in contract_req:
            print(i)
            exchange = i["companyHeader"].split("-")[-1]
            if exchange == " NASDAQ":
                return i["conid"]
            elif exchange == " NYSE":
                return i["conid"]
            else:
                return False
        print(json.dumps(contract_req, indent=2))
    except Exception as e:
        print(f"############################## ERROR While Obtaining Contract ID for {symbol} ##############################")
        print(e)


def check_if_in_pos(con_id, acc_id):
    base_url = settings.IBKR_BASE
    endpoint = f"portfolio/{acc_id}/positions/0"
    print("Calling the in_pos url:", base_url + endpoint)
    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        try:
            in_pos = requests.get(url=base_url + endpoint, verify=False)
            # print(in_pos.text)
            if in_pos is None:
                return False
            else:
                in_pos_json = in_pos.json()
                print(in_pos_json)
                for i in in_pos_json:
                    # print(i)
                    if i["conid"] == con_id and i["conid"] != 0.0:
                        # print("Currently in pos: ", con_id)
                        return False
                return True
        except Exception as e:
            print(e)
        time.sleep(0.5)


def check_if_in_pos_count(con_id, acc_id):
    base_url = settings.IBKR_BASE
    endpoint = f"portfolio/{acc_id}/positions/0"
    print("Calling the in_pos url:", base_url + endpoint)
    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        try:
            in_pos = requests.get(url=base_url + endpoint, verify=False)
            print(in_pos)
            if in_pos is None:
                return False
            else:
                in_pos_json = in_pos.json()
                print(in_pos_json)
                if len(in_pos_json) == 0.0:
                    return True

                return False
        except Exception as e:
            print(e)
        time.sleep(0.5)


def supress(id=None):
    base_url = settings.IBKR_BASE
    endpoint = "iserver/questions/suppress"
    json_body = {
        "messageIds": ["o163", "o354", "o383", "o451", "o10331", "o10151",
                       "o10152",
                       "o10153"
                       ]
    }
    if id is not None:
        json_body["messageIds"].append(id)

    start = time.time()
    while time.time() - start < 5:
        try:
            contract_req = requests.post(url=base_url + endpoint, verify=False, json=json_body).json()
            if contract_req["status"] == "submitted":
                print("Suppressed the following ID's: ", json_body)
                break

        except Exception as e:
            print(e)

        time.sleep(1)


if __name__ == '__main__':
    acc_id = "DUH196417"
    # print(contractSearch(symbol="REBN", type="STK"))
    # open_order(con_id=contractSearch(symbol="CAPT", type="STK"), prc=1.20)
    # print(get_ross_stock())
    # stk = get_ibkr_stocks()
    # print(stk)
    # id = stk[0]["ibkr_id"]
    # historicalData()
    # print(get_snapshot(728763124))
    # get_account_cash("DUH196417")
    # con_id = contractSearch(symbol="CAPT", type="STK")
    # open_order(con_id=con_id, acc_id=acc_id)
    # print(check_if_in_pos(con_id=con_id, acc_id=acc_id))
    # get_scanner_stocks()
