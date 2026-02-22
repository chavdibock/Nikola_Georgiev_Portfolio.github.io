from Classes.EquityAsset import EquityAsset
from math import sqrt, sin, cos


class Stock(EquityAsset):
    def __init__(self, symbol, name, quantity, purchase_price, shares_outstanding):
        super().__init__(symbol, name, quantity, purchase_price)

        self.set_shares_outstanding(shares_outstanding)

    def get_shares_outstanding(self):
        return self.__shares_outstanding

    def set_shares_outstanding(self, shares_outstanding):
        if shares_outstanding is not None and shares_outstanding >= 0:
            self.__shares_outstanding = shares_outstanding
        else:
            self.__shares_outstanding = 0
            raise ValueError("Shares outstanding must be a non-negative value")

    def assess_risk(self):
        prev = self.get_prev_data()
        return sqrt(abs(sin((prev["avg_high"] - prev["avg_low"]) *
                            abs(cos(self.get_shares_outstanding() / self.get_current_price()))))) * 100


if __name__ == '__main__':
    print("Hello")
