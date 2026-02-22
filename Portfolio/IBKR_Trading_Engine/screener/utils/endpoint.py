import requests
import json
import websocket
# Disable SSL Warnings
import urllib3
import ssl
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def historicalData():
    base_url = "http://localhost:5000/v1/api/"
    endpoint = "hmds/history"

    params = {
        "conid": "265598",
        "period": "1w",
        "bar": "1d",
        "outsideRth": "true",
        "barType": "midpoint"
    }

    hd_req = requests.get(url=f"{base_url}{endpoint}", params=params, verify=False)

    print(f"Status Code: {hd_req.status_code}")  # Check response status

    if hd_req.status_code != 200:
        print(f"Error: {hd_req.text}")  # Print raw response (useful for debugging)
        return None

    try:
        hd_json = hd_req.json()
        print(json.dumps(hd_json, indent=2))
    except requests.exceptions.JSONDecodeError:
        print("Error: Response is not valid JSON.")
        print(f"Raw Response: {hd_req.text}")




def contractSearch():
    base_url = "http://localhost:5000/v1/api/"
    endpoint = "iserver/secdef/search"
    json_body = {"symbol": "AAPL", "secType": "STK", "name": False}
    contract_req = requests.post(url=base_url + endpoint, verify=False, json=json_body)
    contract_json = json.dumps(contract_req.json(), indent=2)
    print(contract_json)


def on_message(ws, message):
    print(message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("## CLOSED! ##")


def on_open(ws):
    print("Opened Connection")
    time.sleep(3)
    conids = ["265598", "8314"]
    ws.send('smd+265598+{"fields":["31","83"]}')


if __name__ == "__main__":
    ws = websocket.WebSocketApp(
        url="ws://localhost:5000/v1/api/ws",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
