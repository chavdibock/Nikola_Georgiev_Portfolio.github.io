from Classes.Asset import Asset
import csv


class DebtAsset(Asset):
    def __init__(self, name, symbol, coupon_type, initial_amount, intr_rate):
        super().__init__(symbol, name)
        self.set_coupon_type(coupon_type)
        self.set_initial_amount(initial_amount)
        self.set_interest_rate(intr_rate)

    def set_interest_rate(self, int_rate):
        if int_rate >= 0 and 100 >= int_rate:
            self._interest_rate = int_rate
        else:
            self._interest_rate = 10
            raise ValueError(f"Invalid interest rate for {self.get_symbol()}")

    def get_interest_rate(self):
        return self._interest_rate

    def get_coupon_type(self):
        return self._coupon_type

    def set_coupon_type(self, coupon_type):
        if coupon_type is not None and isinstance(coupon_type, str) \
                and (coupon_type == "year" or coupon_type == "half_year"):
            self._coupon_type = coupon_type
        else:
            self._coupon_type = "year"
            raise ValueError("Coupon type must be a non-empty string and must be equal to 'year' or 'half_year'!!! A DEFAULT value is set!!")

    def get_initial_amount(self):
        return self._initial_amount

    def set_initial_amount(self, initial_amount):
        if initial_amount is not None and initial_amount > 0:
            self._initial_amount = initial_amount
        else:
            self._initial_amount = 1
            raise ValueError("Initial amount must be a positive number. A DEFAULT value is set")

    def get_prev_data(self):

        try:
            path = f"../COS_3040_Python_Project/Prev_Info/{self.get_symbol()}.csv"

            with open(path) as file:
                total_rating = 0
                count = 0
                csv_reader = csv.DictReader(file)
                for row in csv_reader:
                    close_price = float(row["Rating"])
                    total_rating += close_price
                    count += 1
            if count == 0:
                raise f"Empty file for {self.get_symbol()}"
            prev_data = total_rating / count
            return prev_data

        except FileNotFoundError:
            print(f"No Previous data found for {self.get_symbol()}")

    def assess_risk(self):
        raise NotImplementedError("NO implementation")


if __name__ == '__main__':
    print("Hello")
