from Classes import Stock, CryptoCurency, Bond, BankDeposit
import configparser
import csv

if __name__ == '__main__':

    # Parsing the paths for creating the obj
    config = configparser.ConfigParser()
    config.read('config.ini')

    bank_assets_path = config.get('Banks', 'bank_path')
    bond_assets_path = config.get('Bonds', 'bond_path')
    stock_assets_path = config.get('Stocks', 'stock_path')
    crypto_assets_path = config.get('Crypto', 'crypto_path')

    try:
        asset_list = []
        # creating bank deposit objects
        with open(bank_assets_path) as file:
            reader = csv.DictReader(file)
            for i in reader:
                asset_list.append(BankDeposit.BankDeposit(
                    i["name"],
                    i["symb"],
                    i['coup_type'],
                    float(i["initial_amount"]),
                    float(i["interest"]),
                    i["open_date"]))
        # creating bond obj
        with open(bond_assets_path) as file:
            reader = csv.DictReader(file)
            for i in reader:
                asset_list.append(Bond.Bond(
                    i["name"],
                    i["symb"],
                    i['coup_type'],
                    float(i["initial_amount"]),
                    float(i["interest"]),
                    i["expr_date"]
                ))
        # creating stock obj
        with open(stock_assets_path) as file:
            reader = csv.DictReader(file)
            for i in reader:
                asset_list.append(Stock.Stock(
                    i["symb"],
                    i["name"],
                    float(i["quant"]),
                    float(i["prc"]),
                    float(i["oust_shares"])
                ))

        # creating  crypto currency obj
        with open(crypto_assets_path) as file:
            reader = csv.DictReader(file)
            for i in reader:
                asset_list.append(CryptoCurency.Crypto(
                    i["symb"],
                    i["name"],
                    float(i["quant"]),
                    float(i["prc"]),
                    i["blockchain"]
                ))

        sorted_assets = sorted(asset_list, key=lambda asset: asset.assess_risk())

        for i in sorted_assets:
            print(i.get_symbol() + " -> " + i.get_name())
            print(i.assess_risk())

        if sorted_assets[0] == sorted_assets[1]:
            print("Equal")
        else:
            print("Not Equal")


    except ValueError as e:
        print(e)
