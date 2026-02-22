import requests
import urllib3

# Ignore SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class IBApiClient:
    BASE_URL = 'http://35.225.158.232:5000/v1/api/iserver'

    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False

    def get(self, endpoint, **params):
        url = f"{self.BASE_URL}/{endpoint}"
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def secdef_search(self, symbol, listing_exchange):
        data = self.get("secdef/search", symbol=symbol)
        for contract in data:
            if contract.get("description") == listing_exchange:
                conid = contract["conid"]
                months = [
                    sec["months"].split(';')
                    for sec in contract.get("sections", [])
                    if sec.get("secType") == "OPT"
                ]
                return conid, months[0] if months else []
        raise ValueError("Matching listing exchange not found.")

    def get_snapshot_price(self, conid):
        data = self.get("marketdata/snapshot", conids=conid, fields="31")
        return float(data[0].get("31", 0.0))

    def get_valid_strikes(self, conid, month, snapshot_price):
        data = self.get("secdef/strikes", conid=conid, secType="OPT", month=month)
        valid = []
        for opt_type in ('put', 'call'):
            for strike in data.get(opt_type, []):
                if snapshot_price - 30 <= strike <= snapshot_price + 30:
                    valid.append((strike, opt_type[0].upper()))  # 'P' or 'C'
        return valid

    def get_contracts(self, conid, month, strike, right):
        contracts = self.get("secdef/info", conid=conid, month=month, strike=strike, secType="OPT", right=right)
        return [{
            "conid": c["conid"],
            "symbol": c["symbol"],
            "strike": c["strike"],
            "maturityDate": c["maturityDate"],
            "right": right
        } for c in contracts]


def main():
    client = IBApiClient()
    symbol = "HSAI"
    listing_exchange = "NASDAQ"

    try:
        conid, months = client.secdef_search(symbol, listing_exchange)
        snapshot_price = client.get_snapshot_price(conid)

        all_contracts = []
        for month in months:
            for strike, right in client.get_valid_strikes(conid, month, snapshot_price):
                all_contracts.extend(client.get_contracts(conid, month, strike, right))

        num_puts = sum(1 for c in all_contracts if c["right"] == "P")
        num_calls = sum(1 for c in all_contracts if c["right"] == "C")

        if num_calls == 0:
            return "No call options found. Cannot compute Put/Call ratio."

        return f"Put/Call Ratio: {num_puts / num_calls:.2f}"

    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    print(main())
