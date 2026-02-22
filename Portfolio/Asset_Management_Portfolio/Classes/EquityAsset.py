from Classes.Asset import Asset
import csv
from random import random


class EquityAsset(Asset):

    def __init__(self, symbol, name, quantity, purchase_price):
        super().__init__(symbol, name)
        self.set_current_price()
        self.set_purchase_price(purchase_price)
        self.set_quantity(quantity)

    def get_quantity(self):
        return self._quantity

    def set_quantity(self, quantity):
        if quantity is not None and quantity > 0:
            self._quantity = quantity
        else:
            self._quantity = 1
            raise ValueError(f"Quantity for {self.get_name()} must be a non-negative value, A DEFAULT quantity is set")

    def get_purchase_price(self):
        return self._purchase_price

    def set_purchase_price(self, purchase_price):
        if purchase_price is not None and purchase_price >= 0:
            self._purchase_price = purchase_price
        else:
            self._purchase_price = 1
            raise ValueError(f"Purchase price for {self.get_name()} must be a non-negative value, A DEFAULT quantity is set")

    def get_prev_data(self):

        try:
            path = f"../COS_3040_Python_Project/Prev_Info/{self.get_symbol()}.csv"

            with open(path) as file:
                prev_data = {
                    "avg_high": 0,
                    "avg_low": 0,
                    "avg_close": 0

                }
                total_close = 0
                total_high = 0
                total_low = 0

                count = 0
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    close_price = float(row["Close"])
                    low_price = float(row["Low"])
                    high_price = float(row["High"])
                    total_low += low_price
                    total_high += high_price
                    total_close += close_price
                    count += 1
            if count == 0:
                raise f"Empty files for {self.get_symbol()}"

            prev_data["avg_close"] = total_close / count
            prev_data["avg_high"] = total_high / count
            prev_data["avg_low"] = total_low / count
            return prev_data

        except FileNotFoundError:
            print(f"No Previous data found for {self.get_symbol()}")

    def set_current_price(self):
        try:
            average_prev_year = self.get_prev_data()
            if average_prev_year is None:
                return f"No Prev data for {self.get_symbol()}"
            else:
                pmtpl_factor = random()
                self._current_price = average_prev_year["avg_close"] * pmtpl_factor
        except ValueError:
            print(f"No Previous data found for {self.get_symbol()}")

    def get_current_price(self):
        return self._current_price

    def assess_risk(self):
        raise NotImplementedError("NO implementation")


if __name__ == '__main__':
    print("Hello")
