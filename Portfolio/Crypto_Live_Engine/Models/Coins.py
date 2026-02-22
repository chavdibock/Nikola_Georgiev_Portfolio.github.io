import json

from BinanceBot.Helpers.db_crud import MySQLDatabase


class CoinRepository:
    def __init__(self, db: 'MySQLDatabase'):
        self.db = db

    def create_coin(self, symbol, strategy, best_params, is_active, prev_return):
        query = """
            INSERT INTO Coins (symbol, strategy, best_params, is_active, prev_return)
            VALUES (%s, %s, %s, %s, %s);
        """
        params = (symbol, strategy, json.dumps(best_params), is_active, prev_return)
        return self.db.execute_query(query, params)

    def update_in_position(self, symbol, in_position, position_side):
        query = """
            UPDATE Coins
            SET in_position = %s,
                position_side = %s
            WHERE symbol = %s;
        """
        params = (in_position, position_side, symbol)
        return self.db.execute_query(query, params)
    def update_strategy_info_by_symbol(self, symbol, strategy, best_params, is_active, prev_return):
        query = """
            UPDATE Coins
            SET strategy = %s,
                best_params = %s,
                is_active = %s,
                prev_return = %s
            
            WHERE symbol = %s;
        """
        params = (strategy, json.dumps(best_params), is_active, prev_return, symbol)
        return self.db.execute_query(query, params)
    def update_coin(self, symbol, strategy, best_params, is_active, prev_return):
        query = """
            UPDATE Coins
            SET symbol = %s, strategy = %s, best_params = %s, is_active = %s, prev_return = %s
            WHERE id = %s;
        """
        params = (symbol, strategy, json.dumps(best_params), is_active, prev_return)
        return self.db.execute_query(query, params)

    def get_coin_by_symbol(self, symbol):
        query = "SELECT * FROM Coins WHERE symbol = %s LIMIT 1;"
        return self.db.fetch_one(query, (symbol,))
    def delete_coin(self, coin_id):
        query = "DELETE FROM Coins WHERE id = %s;"
        return self.db.execute_query(query, (coin_id,))

    def get_all_coins(self):
        query = "SELECT * FROM Coins;"
        return self.db.fetch_all(query)

    def get_all_coins_sorted_by_prev_return(self, descending=True):
        order = "DESC" if descending else "ASC"
        query = f"SELECT * FROM Coins ORDER BY prev_return {order};"
        return self.db.fetch_all(query)

    def insert_empty_coins(repo):
        TICKERS = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT', 'DOGEUSDT']

        for ticker in TICKERS:
            repo.create_coin(
                symbol=ticker,
                strategy=None,
                best_params=None,
                is_active=None,
                prev_return=None
            )

if __name__ == "__main__":
    db = MySQLDatabase()

    coins = CoinRepository(db)
    coins.insert_empty_coins()
    print(coins.get_all_coins())