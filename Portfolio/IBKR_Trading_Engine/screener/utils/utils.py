import datetime
import json
import threading
import time

import numpy as np
import pandas as pd
import pytz
import requests
from core.config import settings


# DUH196417
def get_account_cash(acc_id):
    base_url = settings.IBKR_BASE
    endpoint = f"portfolio/{acc_id}/summary"

    try:

        acc_req = requests.get(url=base_url + endpoint, verify=False)
        # acc_req_json = json.dumps(acc_req.json(), indent=2)
        cash = acc_req.json()["availablefunds"]["amount"]
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


def scanner_params():
    base_url = settings.IBKR_BASE
    endpoint = "iserver/scanner/params"
    params_req = requests.get(url=base_url + endpoint, verify=False)
    params_json = json.dumps(params_req.json(), indent=2)
    paramFiles = open("scannerParams.json", "w")

    for i in params_json:
        paramFiles.write(i)
    paramFiles.close()
    print(params_req.status_code)


def get_scanner_stocks():
    base_url = settings.IBKR_BASE
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


def get_snapshot(con_id, fields=None):
    base_url = settings.IBKR_BASE
    endpoint = "iserver/marketdata/snapshot"
    if fields is None:
        fields = ["7682", "7762", "7282", "86", "84"]
    scanner_fields = ""
    scanner_fields = ",".join(fields)

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

            res = {
                "ask": float(md_req_js[0]["86"]),
                "bid": float(md_req_js[0]["84"]),
                "avg_volume": float(md_req_js[0]["7282"][:-1]) * (
                    1000 if md_req_js[0]["7282"][-1] == "K" else 1000000 if md_req_js[0]["7282"][-1] == "M" else 1),
                "volume": float(md_req_js[0]["7762"]),
                "change_prc": float(md_req_js[0]["7682"][0:-1])
            }
            # print(res)
            return res
            # md_json = json.dumps(md_req.json(), indent=2)
            # print(md_req)
            # print(md_json)
        except Exception as e:
            print(e)

        time.sleep(1)


def historicalData(contract_id, period='1d', bar='1min'):
    BASE_API_URL = settings.IBKR_BASE
    data = {
        "conids": [contract_id]
    }

    try:
        # Step 1: Get contract details
        r = requests.post(f"{BASE_API_URL}/trsrv/secdef", json=data, verify=False)

        if r.status_code != 200:
            print({"error": f"Failed to get contract details: {r.text}"})

        contract_info = r.json()
        if 'secdef' not in contract_info or not contract_info['secdef']:
            return {"error": "No contract data found."}

        contract = contract_info['secdef'][0]  # Extract contract details

        # Step 2: Fetch historical market data
        r = requests.get(f"{BASE_API_URL}/iserver/marketdata/history",
                         params={"conid": contract_id,
                                 "period": period,
                                 "bar": bar},
                         verify=False)

        res = {}
        if r.status_code != 200:
            # print("RECEIVED 500")
            # print("This is the status code", r.status_code)
            res["error"] = f"Failed to get market data: {r.text}"
            return res
        price_history = r.json()
        if 'data' not in price_history:
            res["error"] = "No price data available."
            return res
            # print(price_history)
            # Return the contract info and market data
        res["error"] = "VALID"
        res["contract"] = contract
        res["price_history"] = price_history
        return res


    except requests.exceptions.RequestException as e:
        res["error"] = f"Request failed: {e}"
        return res


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
    base_url = settings.IBKR_BASE
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


def calculate_vwap(market_data, window=settings.CALC_VWAP_WINDOW):
    try:
        # Extract OHLCV data into a Pandas DataFrame
        ohlcv = pd.DataFrame(market_data['price_history']['data'])

        # Convert columns to numeric, handling potential errors
        ohlcv[['h', 'l', 'c', 'v']] = ohlcv[['h', 'l', 'c', 'v']].apply(pd.to_numeric, errors='coerce')

        # Drop rows with NaN values
        ohlcv.dropna(inplace=True)

        # Compute VWAP using a rolling window
        ohlcv['vwap'] = (ohlcv['c'] * ohlcv['v']).rolling(window=window).sum() / ohlcv['v'].rolling(window=window).sum()

        # Compute percent difference between consecutive VWAP values
        ohlcv['vwap_pct_change'] = ohlcv['vwap'].pct_change() * 100  # Convert to percentage

        # Compute weighted sum of the last 10 percent changes
        calc_window = 5
        if len(ohlcv) >= calc_window + 1:  # Need at least window+1 values for pct_change
            weighted_pct_sum = np.sum(ohlcv['vwap_pct_change'].iloc[-window:].values) / calc_window
        else:
            weighted_pct_sum = np.nan  # Not enough data

        return ohlcv['vwap'].iloc[-1], weighted_pct_sum

    except Exception as e:
        return 0, 0


def calculate_moving_average(market_data, window=9):
    try:
        # Extract OHLCV data into a Pandas DataFrame
        ohlcv = pd.DataFrame(market_data['price_history']['data'])

        # Convert columns to numeric, handling potential errors
        ohlcv[['c']] = ohlcv[['c']].apply(pd.to_numeric, errors='coerce')

        # Drop rows with NaN values
        ohlcv.dropna(inplace=True)

        # Compute Moving Average using a rolling window
        ohlcv['moving_avg'] = ohlcv['c'].rolling(window=window).mean()

        # Compute percent difference between consecutive Moving Average values
        ohlcv['moving_avg_pct_change'] = ohlcv['moving_avg'].pct_change() * 100  # Convert to percentage

        calc_window = 5
        if len(ohlcv) >= calc_window + 1:  # Need at least window+1 values for pct_change
            weighted_pct_sum = np.sum(ohlcv['moving_avg_pct_change'].iloc[-calc_window:].values) / calc_window
        else:
            weighted_pct_sum = np.nan  # Not enough data

        return weighted_pct_sum

    except Exception as e:
        return 0, 0


def calculate_macd(df, length=settings.MACD_LEN, fast=settings.MACD_FAST, slow=settings.MACD_SLOW, signal=9):
    # Ensure 'price_history' and 'data' exist
    price_data = df['price_history']['data']
    closes = [bar['c'] for bar in price_data]  # Extract closing prices
    if len(closes) < max(slow, signal):
        raise ValueError("Not enough data points to compute MACD.")

    # Compute moving averages
    fast_ma = pd.Series(closes).ewm(span=fast, adjust=False).mean()
    slow_ma = pd.Series(closes).ewm(span=slow, adjust=False).mean()

    macd_line = fast_ma - slow_ma
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    hist = macd_line - signal_line

    """
     # Compute rolling correlation to adjust histogram adaptively
    if len(closes) > length:
        correlation = pd.Series(closes).rolling(window=length).corr(pd.Series(range(len(closes))))
        correlation = np.pow(correlation.fillna(0), 2)  # Handle NaN values
        hist = hist * (1 + correlation)
    """

    # Check if the last 3 values of the MACD are increasing and go from negative to positive
    if len(macd_line) >= 3:
        last_three_macd = macd_line.iloc[-3:].tolist()
        macd_condition = False

        # Check if MACD values are increasing and from negative to positive
        if (last_three_macd[0] < 0 and last_three_macd[2] > 0) and last_three_macd[1] > last_three_macd[0] and \
                last_three_macd[2] > last_three_macd[
            1]:
            macd_condition = True

    recent_hist = hist.iloc[-20:]

    lowest_macd_idx = recent_hist.idxmin()
    stop_loss = df.loc[lowest_macd_idx, 'c']

    return hist.iloc[-1], macd_condition, stop_loss


def calculate_adaptive_macd(df, length=settings.MACD_LEN, fast=settings.MACD_FAST, slow=settings.MACD_SLOW, signal=9):
    try:
        try:

            price_data = df['price_history']['data']

        except Exception as e:
            print("#######################")
            print("#######################")
            print(df)
            print("#######################")
            print("#######################")
            print(e)
            print("#######################")
            print("#######################")

        closes = pd.Series([bar['c'] for bar in price_data])

        if len(closes) < max(slow, signal):
            raise ValueError("Not enough data points to compute MACD.")

        # Compute EMAs
        fast_ma = closes.ewm(span=fast, adjust=False).mean()
        slow_ma = closes.ewm(span=slow, adjust=False).mean()

        # MACD line and Signal line
        macd_line = fast_ma - slow_ma
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line

        # Compute rolling correlation (R2 factor)
        if len(closes) > length:
            correlation = closes.rolling(window=length).corr(pd.Series(range(len(closes))))
            correlation = np.power(correlation.fillna(0), 2)  # Handle NaN values
            hist = hist * (1 + correlation)  # Adaptive adjustment

        macd_condition = False
        if len(macd_line) >= 2:
            if hist.iloc[-1] > hist.iloc[-2] and hist.iloc[-1] > 0 and hist.iloc[-2] <= 0:
                macd_condition = True

        return hist.iloc[-1], macd_condition

    except Exception as e:
        print(e)


def get_stop_loss(market_data, period=20):
    df = pd.DataFrame(market_data['price_history']['data'])

    high = df['h']
    low = df['l']
    close = df['c']

    # Calculate True Range (TR)
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Compute ATR using exponential moving average (EMA)
    atr = true_range.ewm(span=period, adjust=False).mean()

    return atr.iloc[-1]


def test_hist_data():
    r = requests.get(f"{settings.IBKR_BASE}/iserver/marketdata/history",
                     params={"conid": 76792991,
                             "period": "1d",
                             "bar": "1min"
                             },
                     verify=False).json()

    hist_data = r["data"]
    print("#############")
    print("#############")
    numbr = int(hist_data[-1]["t"])
    print(numbr)
    tm = datetime.datetime.fromtimestamp(numbr / 1000)
    print(tm.strftime('%Y-%m-%d %H:%M:%S'))
    print("Total len:", len(hist_data))

    print("#############")
    print("#############")


if __name__ == '_main_':
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
    # adjust_scanner_data(0)
