from Classes.DebtAsset import DebtAsset
from math import sin, sqrt, cos

from datetime import datetime


class BankDeposit(DebtAsset):
    def __init__(self, name, symbol, coupon_type, initial_amount, intr_rate, opening_date):
        super().__init__(name, symbol, coupon_type, initial_amount, intr_rate)
        self.set_opening_date(opening_date)

    def get_opening_date(self):
        return self.__opening_date

    def set_opening_date(self, opening_date):
        if opening_date is not None:
            try:
                self.__opening_date = datetime.strptime(opening_date, "%Y-%m-%d")

            except ValueError:
                raise ValueError("Invalid opening date format. Please use YYYY-MM-DD format.")
        else:
            raise ValueError("Opening date cannot be None.")

    def current_return(self):
        current_date = datetime.now()
        if self.get_coupon_type() == "half_year":
            # Calculate the number of months passed
            months = (current_date.year - self.get_opening_date().year) * 12 + current_date.month - self.get_opening_date().month
            half_years = int(months / 6)
            roi = self.get_initial_amount() * (1 + self.get_interest_rate() / 100) ** half_years

        else:
            # Calculate the number of months passed
            months = (current_date.year - self.get_opening_date().year) * 12 + current_date.month - self.get_opening_date().month
            half_years = int(months / 12)
            roi = self.get_initial_amount() * (1 + self.get_interest_rate() / 100) ** half_years

        return roi

    def assess_risk(self):
        prev = self.get_prev_data()
        return sqrt(abs(sin(prev) * cos(self.get_initial_amount()))) * 100


if __name__ == '__main__':
    print("Hello")
