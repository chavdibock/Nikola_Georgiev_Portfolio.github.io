import unittest
from Classes.EquityAsset import EquityAsset


class TestEquityAsset(unittest.TestCase):
    def setUp(self):
        self.equity_asset = EquityAsset("APPL", "Apple Inc.", 100, 150.0)

    def test_get_quantity(self):
        self.assertEqual(self.equity_asset.get_quantity(), 100)

    def test_set_quantity_valid(self):
        self.equity_asset.set_quantity(200)
        self.assertEqual(self.equity_asset.get_quantity(), 200)

    def test_set_quantity_invalid(self):
        with self.assertRaises(ValueError):
            self.equity_asset.set_quantity(-50)

    def test_get_purchase_price(self):
        self.assertEqual(self.equity_asset.get_purchase_price(), 150.0)

    def test_set_purchase_price_valid(self):
        self.equity_asset.set_purchase_price(200.0)
        self.assertEqual(self.equity_asset.get_purchase_price(), 200.0)

    def test_set_purchase_price_invalid(self):
        with self.assertRaises(ValueError):
            self.equity_asset.set_purchase_price(-100.0)


if __name__ == '__main__':
    unittest.main()
