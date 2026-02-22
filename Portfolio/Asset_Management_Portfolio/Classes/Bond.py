from Classes.DebtAsset import DebtAsset
from math import sin, cos
from datetime import datetime


class Bond(DebtAsset):
    def __init__(self, name, symbol, coupon_type, initial_amount, intr_rate, expiration_date):
        super().__init__(name, symbol, coupon_type, initial_amount, intr_rate)
        self.set_expiration_date(expiration_date)

    def get_expiration_date(self):
        return self.__expiration_date

    def set_expiration_date(self, expiration_date):
        if expiration_date is not None:
            try:
                self.__expiration_date = datetime.strptime(expiration_date, "%Y-%m-%d")
            except ValueError:
                self.__expiration_date = datetime.now()
                raise ValueError("Invalid expiration date format. Please use YYYY-MM-DD format. A default Value is set")

        else:
            self.__expiration_date = datetime.now()
            raise ValueError("Expiration date cannot be None. A default Value is set")

    def remaining_return(self):
        current_date = datetime.now()
        if self.get_coupon_type() == "half_year":
            # Calculate the number of months passed
            months = (self.get_expiration_date().year - current_date.year) * 12 + current_date.month - self.get_expiration_date().month
            half_years = int(months / 6)
            roi = (self.get_initial_amount() * (1 + self.get_interest_rate() / 100) - self.get_initial_amount()) * half_years

        else:
            # Calculate the number of months passed
            months = (self.get_expiration_date().year - current_date.year) * 12 + current_date.month - self.get_expiration_date().month
            half_years = int(months / 12)
            roi = (self.get_initial_amount() * (1 + self.get_interest_rate() / 100) - self.get_initial_amount()) * half_years

        return roi

    def assess_risk(self):
        prev = self.get_prev_data()
        return abs(sin(prev) ** cos(self.get_initial_amount())) * 100


if __name__ == '__main__':
    print("Hello")
