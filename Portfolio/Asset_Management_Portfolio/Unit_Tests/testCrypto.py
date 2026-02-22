import unittest
from Classes.CryptoCurency import Crypto


class TestCrypto(unittest.TestCase):
    def setUp(self):
        self.crypto_asset = Crypto("BTC", "Bitcoin", 10, 60000.0, "Proof-of-Work")

    def test_get_blockchain(self):
        self.assertEqual(self.crypto_asset.get_blockchain(), "Proof-of-Work")

    def test_set_blockchain_valid(self):
        self.crypto_asset.set_blockchain("Proof-of-Stake")
        self.assertEqual(self.crypto_asset.get_blockchain(), "Proof-of-Stake")

    def test_set_blockchain_invalid(self):
        with self.assertRaises(ValueError):
            self.crypto_asset.set_blockchain(None)



if __name__ == '__main__':
    unittest.main()
