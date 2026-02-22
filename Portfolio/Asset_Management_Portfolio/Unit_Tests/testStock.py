import unittest
from Classes.Stock import Stock


class TestStock(unittest.TestCase):
    def setUp(self):
        self.stock_asset = Stock("APPL", "Apple Inc.", 100, 150.0, 1000000)

    def test_get_shares_outstanding(self):
        self.assertEqual(self.stock_asset.get_shares_outstanding(), 1000000)

    def test_set_shares_outstanding_valid(self):
        self.stock_asset.set_shares_outstanding(2000000)
        self.assertEqual(self.stock_asset.get_shares_outstanding(), 2000000)

    def test_set_shares_outstanding_invalid(self):
        with self.assertRaises(ValueError):
            self.stock_asset.set_shares_outstanding(-50000)



if __name__ == '__main__':
    unittest.main()
