import unittest
from datetime import datetime
from Classes.BankDeposit import BankDeposit


class testBankDeposit(unittest.TestCase):
    def setUp(self):
        self.bank_deposit = BankDeposit("Savings", "UNCR", "half_year", 1000, 5, "2022-01-01")

    def test_get_opening_date(self):
        self.assertEqual(self.bank_deposit.get_opening_date(), datetime(2022, 1, 1))

    def test_set_opening_date_valid(self):
        self.bank_deposit.set_opening_date("2023-01-01")
        self.assertEqual(self.bank_deposit.get_opening_date(), datetime(2023, 1, 1))

    def test_set_opening_date_invalid_format(self):
        with self.assertRaises(ValueError):
            self.bank_deposit.set_opening_date("2023/01/01")

    def test_current_return_half_year(self):
        self.bank_deposit = BankDeposit("Banka DSK", "DSK", "half_year", 1000, 5, "2022-01-01")
        self.assertAlmostEqual(self.bank_deposit.current_return(), 1215.50625, places=3)

    def test_current_return_annual(self):
        self.bank_deposit = BankDeposit("Banka DSK", "DSK", "year", 1000, 5, "2022-01-01")
        self.assertAlmostEqual(self.bank_deposit.current_return(), 1102.5, places=3)

    def test_assess_risk(self):
        # Mocking get_prev_data method
        self.bank_deposit.get_prev_data = lambda: 1000  # Mock previous data
        self.assertAlmostEqual(self.bank_deposit.assess_risk(), 68.19235677171368, places=3)


if __name__ == '__main__':
    unittest.main()
