import requests
import time
import json
import concurrent.futures
from core.config import settings
import statistics


def get_biggest_gainers():
    pass


def our_rel_volume(avg_90_d, volume_long):
    if volume_long >= 3 * avg_90_d:
        return True
    else:
        return False


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
    # print("This are the contracts: ", scan_req.json()["contracts"])
    res = []
    for i in scan_req.json()["contracts"]:
        res.append(i)
    # print(scan_req.status_code)
    # print(res)
    return res


def adjust_scanner_data(min_prc_change):
    # 82 Change Since Open - The difference between the last price and the open price.
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


def get_snapshot(con_id, fields, symbol, comp_name):
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
            if all(key in md_req_js[0].keys() for key in fields):
                missing_keys = [key for key in fields if key not in md_req_js[0].keys()]

                if not missing_keys:  # All required keys exist
                    res["ask"] = float(md_req_js[0]["86"])
                    res["bid"] = float(md_req_js[0]["84"])
                    res["avg_volume"] = float(md_req_js[0]["7282"][:-1]) * (
                        1000 if md_req_js[0]["7282"][-1] == "K" else 1000000 if md_req_js[0]["7282"][-1] == "M" else 1)
                    res["volume"] = float(md_req_js[0]["7762"])
                    res["change_prc"] = float(md_req_js[0]["83"])  # Might be missing in some cases
                    res["symbol"] = symbol
                    res["company_name"] = comp_name
                    res["con_id"] = con_id
                    res["status"] = "Valid"
                else:
                    res["status"] = "Invalid"
                    print(f"Missing keys: {missing_keys}")  # Debugging output
            # print("success")
            break

        # md_json = json.dumps(md_req.json(), indent=2)
        # print(md_req)
        # print(md_json)
        except Exception as e:
            # print(md_req.json())
            print(e)
        time.sleep(1)
    return res


def fetch_snapshot(stock):
    return get_snapshot(stock["con_id"], ["7762", "7282", "86", "84"], stock["symbol"], stock["company_name"])


def get_all_snapshots(stocks):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(fetch_snapshot, stocks))  # Convert to list

    # Filter out invalid results
    valid_results = [result for result in results if result.get("status") == "Valid"]

    return valid_results


def screener():
    stocks = get_scanner_stocks()

    fields = ["7682", "7762", "7282", "86", "84"]
    cur_data = []

    snapshots = get_all_snapshots(stocks=stocks)

    for i in snapshots:
        i["prc_change_seq"] = [i["ask"]]
        i["int_prc_change"] = [i["change_prc"]]
        cur_data.append(i)

    # print(cur_data)
    start_time = time.time()
    timeout = 60 * 2
    while time.time() - start_time < timeout:
        time.sleep(60)
        print("Retaking new prc change")
        cur_snap_stocks = get_all_snapshots(cur_data)
        for i in range(0, len(cur_data)):
            cur_data[i]["prc_change_seq"].append(cur_snap_stocks[i]["ask"])
            cur_data[i]["int_prc_change"].append(cur_snap_stocks[i]["change_prc"])

        # print(cur_data)

    for i in cur_data:
        arr = i["int_prc_change"]
        percent_changes = [(arr[i] - arr[i - 1]) / arr[i - 1] * 100 for i in range(1, len(arr))]
        weights = arr[:-1]
        # Compute weighted sum
        weighted_sum = sum(p * w for p, w in zip(percent_changes, weights)) / sum(weights)
        i["w_sum"] = weighted_sum

    sorted_arr = sorted(cur_data, key=lambda x: x["w_sum"], reverse=True)

    return sorted_arr


if __name__ == '__main__':
    print(get_scanner_stocks())
