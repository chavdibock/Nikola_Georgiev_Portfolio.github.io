import unittest
from datetime import datetime
from Classes.Bond import Bond


class TestBond(unittest.TestCase):
    def setUp(self):
        self.bond_asset = Bond("Balgarska narodna banka", "BNB", "year", 1000, 5, "2025-01-01")

    def test_get_expiration_date(self):
        self.assertEqual(self.bond_asset.get_expiration_date(), datetime(2025, 1, 1))

    def test_set_expiration_date_valid(self):
        self.bond_asset.set_expiration_date("2030-01-01")
        self.assertEqual(self.bond_asset.get_expiration_date(), datetime(2030, 1, 1))

    def test_set_expiration_date_invalid_format(self):
        with self.assertRaises(ValueError):
            self.bond_asset.set_expiration_date("2030/01/01")

    def test_set_expiration_date_none(self):
        with self.assertRaises(ValueError):
            self.bond_asset.set_expiration_date(None)

    def test_remaining_return_half_year(self):
        self.bond_asset = Bond("Corporate Bond", "USNB", "year", 1000, 2.5, "2029-01-01")
        self.assertAlmostEqual(self.bond_asset.remaining_return(), 125, places=3)

    def test_remaining_return_annual(self):
        self.bond_asset = Bond("Corporate Bond", "USNB", "year", 1000, 5, "2025-01-01")
        self.assertAlmostEqual(self.bond_asset.remaining_return(), 50, places=3)

    def test_assess_risk(self):
        # Mocking get_prev_data method
        self.bond_asset.get_prev_data = lambda: 1000  # Mock previous data
        self.assertAlmostEqual(self.bond_asset.assess_risk(),  89.86099989713796, places=3)


if __name__ == '__main__':
    unittest.main()
