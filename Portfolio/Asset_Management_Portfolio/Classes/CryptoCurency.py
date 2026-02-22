from Classes.EquityAsset import EquityAsset
from math import sin, sqrt, cos


class Crypto(EquityAsset):
    def __init__(self, symbol, name, quantity, purchase_price, blockchain):
        super().__init__(symbol, name, quantity, purchase_price)
        self.set_blockchain(blockchain)
        self.set_current_price()

    def get_blockchain(self):
        return self._blockchain

    def set_blockchain(self, blockchain):
        if blockchain is not None and isinstance(blockchain, str):
            self._blockchain = blockchain
        else:
            self._blockchain = "No blockcahin"
            raise ValueError("Blockchain must be a non-empty string")

    def assess_risk(self):
        prev = self.get_prev_data()
        return sqrt(abs(sin((prev["avg_high"] + prev["avg_low"]) * abs(cos(sqrt(self.get_current_price())))))) * 100


if __name__ == '__main__':
    print("Hello")
