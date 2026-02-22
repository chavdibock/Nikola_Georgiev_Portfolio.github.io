import json
import threading
import time
import websocket
import datetime
import requests
import csv
from tradingview_screener import Query, Column  # 'BINANCE:BTCUSDT'
import numpy as np
from core.config import settings
import pytz


class AGCWebSocket:
    def __init__(self, address, q, ticker, event_loop):
        self.queue = q
        self.address = address
        self.ticker = ticker  # Store the ticker symbol
        self.ws = None
        self.event_loop = event_loop

    def on_message(self, ws, message):
        js_m = json.loads(message)
        if isinstance(js_m, list):  # Check if the message is a list
            for item in js_m:  # Iterate through the list
                if isinstance(item, dict) and item.get("c") is not None:
                    # print("Valid dictionary inside the list, adding to queue")
                    self.queue.put(item)

    def on_error(self, ws, error):
        print(f"Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(f"WebSocket connection closed with code {close_status_code} and message: {close_msg}")

    def on_open(self, ws):
        print("WebSocket connection opened")
        header = {
            "action": "auth",
            "key": config_dictionary['key'],
            "secret": config_dictionary['secret']
        }
        # Send subscription message with the ticker symbol
        subscribe_message = {
            "action": "subscribe",
            "bars": [self.ticker]
            # "symbols": [self.ticker]  # Subscribe to the specific ticker
        }
        ws.send(json.dumps(header))
        ws.send(json.dumps(subscribe_message))  # Send subscription message

    def on_ping(self, ws, message):
        print(f"{datetime.datetime.utcnow()} Received ping: {message}")
        ws.send(message, websocket.ABNF.OPCODE_PONG)
        print(f"Sent pong: {message}")

    def open_connection(self):
        self.ws = websocket.WebSocketApp(self.address,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         on_open=self.on_open,
                                         on_ping=self.on_ping)
        websocket.enableTrace(False)
        self.ws.run_forever()

    def close_connection(self):
        if self.ws:
            self.ws.close()
            self.ws = None
            print("WebSocket connection closed")


def manage_connection(addr, q, ticker, event_loop):
    web_sock = AGCWebSocket(address=addr, q=q, ticker=ticker, event_loop=event_loop)

    def start_ws():
        web_sock.open_connection()

    while True:
        try:
            # Run WebSocket in a separate thread
            ws_thread = threading.Thread(target=start_ws)
            ws_thread.start()

            # Wait for the WebSocket thread to close or crash
            ws_thread.join()  # This will block until the thread terminates

            print(f"{datetime.datetime.utcnow()} Connection closed. Restarting...")

            # Wait a bit before trying to reopen the connection
            time.sleep(3)

        except Exception as e:
            print(f"ERROR with the websocket: {e}")
            time.sleep(3)  # Wait before retrying


# DUH196417
def get_account_cash(acc_id):
    base_url = settings.ibkr_client
    endpoint = f"portfolio/{acc_id}/summary"

    try:

        acc_req = requests.get(url=base_url + endpoint, verify=False)
        # acc_req_json = json.dumps(acc_req.json(), indent=2)
        cash = acc_req.json()["availablefunds"]["amount"]
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


def open_order(con_id, acc_id):
    base_url = settings.ibkr_client
    endpoint = "iserver/account/DUH196417/orders"
    time.sleep(0.5)
    prc = get_snapshot(con_id=con_id, fields=None)
    print(con_id)
    print(prc)
    time.sleep(1)
    available_cash = get_account_cash(acc_id)
    time.sleep(1)
    qty = int((0.2 * available_cash) / prc["ask"])

    if qty > 24500:
        qty = 20000

    prf_price = round_price(prc["ask"] * 1.05, point=3)

    st_price = round_price(prc["ask"] * 0.96, point=3)
    # print(st_price)
    mrk_ord = f"{datetime.datetime.now().timestamp()}_MRK"

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


def contractSearch(symbol, type):
    base_url = settings.ibkr_client
    endpoint = "iserver/secdef/search"
    json_body = {"symbol": symbol, "type": type, "name": False, }
    try:

        contract_req = requests.post(url=base_url + endpoint, verify=False, json=json_body).json()
        # return contract_req

        for i in contract_req:
            exchange = i["companyHeader"].split("-")[-1]
            if exchange == " NASDAQ":
                return i["conid"]
            elif exchange == " NSE":
                return i["conid"]
            else:
                return False
        print(json.dumps(contract_req, indent=2))

    except Exception as e:
        print(f"############################## ERROR While Obtaining Contract ID for {symbol} ##############################")
        print(e)


def scanner_params():
    base_url = settings.ibkr_client
    endpoint = "iserver/scanner/params"
    params_req = requests.get(url=base_url + endpoint, verify=False)
    params_json = json.dumps(params_req.json(), indent=2)
    paramFiles = open("scannerParams.json", "w")

    for i in params_json:
        paramFiles.write(i)
    paramFiles.close()
    print(params_req.status_code)


def get_scanner_stocks():
    base_url = settings.ibkr_client
    endpoint = "iserver/scanner/run"
    scan_body = {
        "instrument": "STK",
        "location": "STK.US.MAJOR",
        "type": "TOP_PERC_GAIN",
        "filter": [
            {
                "code": "priceAbove",
                "value": 2
            },
            {
                "code": "priceBelow",
                "value": 15
            },
            {
                "code": "marketCapAbove1e6",
                "value": 350
            }
        ]
    }
    scan_req = requests.post(url=base_url + endpoint, verify=False, json=scan_body)
    scan_json = json.dumps(scan_req.json(), indent=2)
    res = []
    for i in scan_req.json()["contracts"]:
        res.append(i)
    # print(scan_req.status_code)
    # print(res)
    return res


def our_rel_volume(avg_90_d, volume_long):
    if volume_long > 3 * avg_90_d:
        return True
    else:
        return False


def adjust_scanner_data(min_prc_change):
    # 7682 Change Since Open - The difference between the last price and the open price.
    # 7762 Volume Long - High precision volume for the day. For formatted volume refer to field 87.
    # 7282 Average Volume

    stocks = get_scanner_stocks()

    fields = ["7682", "7762", "7282", "86", "84"]
    cur_data = []

    for stock in stocks:
        print(f"Getting snapshots for the stocks {stock['symbol']} ")
        data = get_snapshot(con_id=stock["con_id"], fields=fields)
        if data is not False:
            if our_rel_volume(avg_90_d=data["avg_volume"], volume_long=data["volume"]) is True:
                data["con_id"] = stock["con_id"]
                data["prc_chg_arr"] = [data["change_prc"]]
                cur_data.append(data)

    start_time = time.time()
    timeout = 60 * 7
    print("Starting to check every min")
    while time.time() - start_time < timeout:

        time.sleep(60)
        print("Retaking new prc change")
        for data in cur_data:
            cur_snapshot = get_snapshot(con_id=data["con_id"], fields=fields)
            data["prc_chg_arr"].append(cur_snapshot["change_prc"])

    # [28.07, 20.2, 23.4, 23.4]
    print("Starting to weight each change")
    for i in cur_data:
        arr = i["prc_chg_arr"]
        percent_changes = [(arr[i] - arr[i - 1]) / arr[i - 1] * 100 for i in range(1, len(arr))]
        weights = arr[:-1]
        # Compute weighted sum
        weighted_sum = sum(p * w for p, w in zip(percent_changes, weights)) / sum(weights)
        i["w_sum"] = weighted_sum

    sorted_arr = sorted(cur_data, key=lambda x: x["w_sum"], reverse=True)
    print(cur_data)
    print(sorted_arr)

    return sorted_arr


def get_ross_stock():
    a = Query().select('name', 'logoid', 'close').set_tickers().set_markets('america').where(
        Column('change') >= 20,
        Column('exchange') == 'NASDAQ',
        Column('relative_volume_10d_calc') > 6,
        Column('close').between(left=2, right=15)
    ).order_by(column='relative_volume_10d_calc', ascending=False).get_scanner_data()

    return a


def get_z_score_assets(deviation):
    """

    :param deviation: The number or the std
    :return:
    """
    std_data = calculate_score()
    print(std_data)
    a = Query().select('name', 'logoid', 'close').set_tickers().set_markets('america').where(
        Column('change') >= 15,
        Column('close').between(left=1, right=15),
        Column('relative_volume_10d_calc') > 5,
        Column('price_book_ratio') <= std_data["PB_mean"] - deviation * std_data["PB_std"],
        Column('exchange') == 'NASDAQ',
        # Column('price_sales_ratio') >= std_data["PS_mean"] - deviation * std_data["PS_std"],
        # Column('price_earnings_ttm') >= std_data["PE_mean"] - deviation * std_data["PE_std"],
        # Column('earnings_per_share_basic_ttm') >= std_data["ES_mean"] - deviation * std_data["ES_std"],
        Column('float_shares_outstanding') >= 20000000
    ).order_by(column='change', ascending=False).get_scanner_data()

    return a


def calculate_score():
    s_p = get_s_p_500_data()

    # Ensure this function provides the correct data
    PE_list, PB_list, ES_list, PS_list = [], [], [], []

    def is_valid_number(value):
        """Checks if the value is a valid finite number within reasonable bounds."""
        try:
            val = float(value)
            return np.isfinite(val) and -1e3 < val < 1e3  # Define reasonable bounds
        except (ValueError, TypeError):
            return False

    for i in s_p:
        try:
            # Append valid data only
            if i.get('Price/Earnings') and is_valid_number(i['Price/Earnings']):
                PE_list.append(float(i['Price/Earnings']))
            if i.get('Price/Book') and is_valid_number(i['Price/Book']):
                PB_list.append(float(i['Price/Book']))
            if i.get('Earnings/Share') and is_valid_number(i['Earnings/Share']):
                ES_list.append(float(i['Earnings/Share']))
            if i.get('Price/Sales') and is_valid_number(i['Price/Sales']):
                PS_list.append(float(i['Price/Sales']))
        except Exception as e:
            print(f"Skipping invalid data: {i} due to error: {e}")

    # Filter out invalid numbers before calculation
    PE_list = [x for x in PE_list if is_valid_number(x)]
    PB_list = [x for x in PB_list if is_valid_number(x)]
    ES_list = [x for x in ES_list if is_valid_number(x)]
    PS_list = [x for x in PS_list if is_valid_number(x)]

    # Safeguard against invalid lists
    def safe_mean(arr):
        return np.mean(arr) if arr and np.isfinite(np.mean(arr)) else float('nan')

    def safe_std(arr):
        return np.std(arr) if arr and np.isfinite(np.std(arr)) else float('nan')

    # Compile results with safety checks
    a = {
        "PE_mean": safe_mean(PE_list),
        "PB_mean": safe_mean(PB_list),
        "ES_mean": safe_mean(ES_list),
        "PS_mean": safe_mean(PS_list),
        "PE_std": safe_std(PE_list),
        "PB_std": safe_std(PB_list),
        "ES_std": safe_std(ES_list),
        "PS_std": safe_std(PS_list)
    }

    return a


def get_sectors():
    s_p = get_s_p_500_data()
    list_sectors = []
    for i in s_p:
        # if i['Sector'] =
        list_sectors.append(i['Sector'])
    print(len(set(list_sectors)))

    for i in set(list_sectors):
        print(i)


def get_s_p_500_data():
    url = "https://datahub.io/core/s-and-p-500-companies-financials/_r/-/data/constituents-financials.csv"

    with requests.Session() as s:
        download = s.get(url)

        decoded_content = download.content.decode('utf-8')

        cr = csv.DictReader(decoded_content.splitlines(), delimiter=',')
        dict_list = [row for row in cr]
        return dict_list


def get_ibkr_stocks():
    stocks = get_ross_stock()
    print(stocks[1])
    print(type(stocks[1]))
    res = []
    for _, row in stocks[1].iterrows():  # Iterating over rows
        con_id = contractSearch(symbol=row["name"], type="STK")
        res.append(
            {
                "ibkr_id": con_id,
                "symbol": row["name"]
            }
        )
    return res


def get_snapshot(con_id, fields):
    base_url = settings.ibkr_client
    endpoint = "iserver/marketdata/snapshot"
    if fields is None:
        fields = ["7682", "7762", "7282", "86", "84"]
    scanner_fields = ""
    scanner_fields = ",".join(fields)

    print(scanner_fields)
    conid = f"conids={con_id}"
    fields = f"fields={scanner_fields}"
    params = "&".join([conid, fields])
    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        try:

            request_url = "".join([base_url, endpoint, "?", params])
            md_req = requests.get(url=request_url, verify=False)
            if md_req is None:
                return False

            md_req_js = md_req.json()
            # print("This is the response")
            # print(md_req_js)

            res = {
                "ask": float(md_req_js[0]["86"]),
                "bid": float(md_req_js[0]["84"]),
                "avg_volume": float(md_req_js[0]["7282"][:-1]) * (
                    1000 if md_req_js[0]["7282"][-1] == "K" else 1000000 if md_req_js[0]["7282"][-1] == "M" else 1),
                "volume": float(md_req_js[0]["7762"]),
                "change_prc": float(md_req_js[0]["7682"][0:-1])
            }
            return res
            # md_json = json.dumps(md_req.json(), indent=2)
            # print(md_req)
            # print(md_json)
        except Exception as e:
            print(e)

        time.sleep(1)


def historicalData():
    base_url = settings.ibkr_client
    endpoint = "hmds/history"
    conid = "conid=265598"
    period = "period=min"
    bar = "bar=1d"
    outsideRth = "outsideRth=true"
    barType = "barType=midpoint"
    params = "&".join([conid, period, bar, outsideRth, barType])
    request_url = "".join([base_url, endpoint, "?", params])
    hd_req = requests.get(url=request_url, verify=False)
    hd_json = json.dumps(hd_req.json(), indent=2)
    print(hd_req)
    print(hd_json)


def check_if_in_pos(con_id, acc_id):
    base_url = settings.ibkr_client
    endpoint = f"portfolio/{acc_id}/positions/0"
    print("Calling the in_pos url:", base_url + endpoint)
    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        try:
            in_pos = requests.get(url=base_url + endpoint, verify=False)
            print(in_pos.text)
            if in_pos is None:
                return False
            else:
                in_pos_json = in_pos.json()
                # print(in_pos_json)
                for i in in_pos_json:
                    # print(i)
                    if i["conid"] == con_id and i["position"] != 0.0:
                        # print("Currently in pos: ", con_id)
                        return True
                return False
        except Exception as e:
            print(e)
        time.sleep(0.5)


def supress(id=None):
    base_url = settings.ibkr_client
    endpoint = "iserver/questions/suppress"
    json_body = {
        "messageIds": ["o163", "o354", "o383", "o451", "o10331"]
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


def is_market_open():
    # Get current time in New York timezone
    ny_tz = pytz.timezone("America/New_York")
    now = datetime.datetime.now(ny_tz).time()  # Extract only the time part

    # Market open time: 9:30 AM, Market close time: 4:00 PM
    market_open = datetime.time(9, 30)
    market_close = datetime.time(16, 0)

    return market_open <= now <= market_close


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
    adjust_scanner_data(0)
