import unittest
from unittest.mock import patch
from Classes.DebtAsset import DebtAsset


class TestDebtAsset(unittest.TestCase):
    def setUp(self):
        self.debt_asset = DebtAsset("Bulgarian National Bond", "BNB", "year", 1000, 5)

    def test_get_coupon_type(self):
        self.assertEqual(self.debt_asset.get_coupon_type(), "year")

    def test_set_coupon_type_valid(self):
        self.debt_asset.set_coupon_type("half_year")
        self.assertEqual(self.debt_asset.get_coupon_type(), "half_year")

    def test_set_coupon_type_invalid(self):
        with self.assertRaises(ValueError):
            self.debt_asset.set_coupon_type("quarterly")

    def test_set_coupon_type_none(self):
        with self.assertRaises(ValueError):
            self.debt_asset.set_coupon_type(None)

    def test_get_initial_amount(self):
        self.assertEqual(self.debt_asset.get_initial_amount(), 1000)

    def test_set_initial_amount_valid(self):
        self.debt_asset.set_initial_amount(2000)
        self.assertEqual(self.debt_asset.get_initial_amount(), 2000)

    def test_set_initial_amount_invalid(self):
        with self.assertRaises(ValueError):
            self.debt_asset.set_initial_amount(-500)

    @patch("Classes.DebtAsset.DebtAsset.get_prev_data")
    def test_get_prev_data(self, mock_get_prev_data):
        mock_get_prev_data.return_value = 3.5
        self.assertEqual(self.debt_asset.get_prev_data(), 3.5)

    @patch("Classes.DebtAsset.DebtAsset.get_prev_data")
    def test_get_prev_data_empty_file(self, mock_get_prev_data):
        mock_get_prev_data.side_effect = FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.debt_asset.get_prev_data()


if __name__ == '__main__':
    unittest.main()
