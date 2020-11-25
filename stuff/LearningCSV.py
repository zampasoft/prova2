#
import csv
from datetime import datetime
import pandas as pd
import os


class AssetClass:
    def __init__(self, asset_type: str, buy_commission: float, annual_fee: float, tax_rate: float = 0.26):
        """
        :type asset_type: str
        :type annual_fee: float
        :type buy_commission: float
        """
        # Asset Classes that I focus on
        # this is useful for historical analysis
        AssetClasses = ("equity", "ETC", "ETF", "currency")
        if asset_type in AssetClasses:
            self.assetType = asset_type
            self.hadDividends = asset_type in ("equity", "ETF")
        else:
            raise ValueError
        if 0 <= buy_commission < 1:
            self.buyCommission = buy_commission
        else:
            raise ValueError
        if 0 <= annual_fee < 1:
            self.annualFee = annual_fee
        else:
            raise ValueError
        if 0.0 <= tax_rate < 1.0:
            self.tax_rate = tax_rate
        else:
            raise ValueError

    def hasDividends(self):
        return self.hadDividends

    def __str__(self):
        return self.assetType


# I create the asset classes I want in my Portfolio for now
EQUITY = AssetClass("equity", 0.005, 0)
ETC = AssetClass("ETC", 0.005, 0)
CURRENCY = AssetClass("currency", 0.001, 0)


# I define the concept of Asset
class Asset:
    def __init__(self, assetType: AssetClass, name: str, symbol: str, market: str, currency: str,
                 history: pd.DataFrame = pd.DataFrame()):
        self.assetType = assetType
        self.name = name
        self.symbol = symbol
        self.market = market
        self.currency = currency
        # self.avg_buy_price = avg_buy_price  # this is in the actual asset currency
        # self.avg_buy_curr_chg = avg_buy_curr_chg  # this is the average exchange from asset curr. to default one (EURO)
        self.history = history

    def __str__(self):
        # return self.symbol + "\t" + self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)
        return self.name + "\t" + str(self.assetType)





print("\nTesting CSV Reader")
filename = "./TestCSV.csv"

with open(filename, newline='') as csvfile:
    spamreader = csv.reader(csvfile, dialect='excel')
    first_row = True
    for row in spamreader:
        if first_row:
            print("TITLES")
            print(row)
            first_row = False
        else:
            # we expect DATE, VERB, SYMBOL
            dd = datetime.strptime(row[0], '%d/%m/%Y')
            verb = row[1]
            symbol = row[2]
            fullname = row[3]
            print(str(dd) + "\t" + verb + "\t" + symbol + "\t" + fullname)


#Testing CSV Writer
assets = dict()
assets["BLK"] = Asset(EQUITY, "BlackRock, Inc.", "BLK", "NYSE", "USD")
assets["DBX"] = Asset(EQUITY, "Dropbox, Inc.", "DBX", "NASDAQ", "USD")
assets["AVGO"] = Asset(EQUITY, "Broadcom Inc.", "AVGO", "NASDAQ", "USD")

print("\nTesting CSV Writer")
csv_file = "./TestWriteCSV.csv"
csv_columns = ["SYMBOL", "Full Name", "Asset Class", "Market", "Currency"]
with open(csv_file, 'w', newline='') as csvfile:
    # write header
    writer = csv.writer(csvfile, lineterminator=os.linesep)
    writer.writerow(csv_columns)
    for key in assets:
        print(assets[key])
        data = assets[key]
        assert isinstance(data, Asset), "Input variables should belong to class Asset"
        writer.writerow([data.symbol, data.name, data.assetType, data.market, data.currency])

with open(csv_file, "r", newline='') as csvfile:
    for row in csvfile:
        print(row)