# loading the class data from the package pandas_datareader
from typing import List

from pandas_datareader import data

# Asset Classes that I focus on
class AssetClass:
    def __init__(self, assetType: str, buyCommission: float, annualFee: float) -> object:
        """

        :type buyCommission: float
        """
        AssetClasses = ("equity", "ETC", "ETF", "currency")
        if assetType in AssetClasses:
            self.assetType = assetType
            self.hadDividends =  assetType in ("equity", "ETF")
        else:
            raise ValueError
        if 0 <= buyCommission < 1:
            self.buyCommission = buyCommission
        else:
            raise ValueError
        if 0 <= annualFee < 1:
            self.annualFee = annualFee
        else:
            raise ValueError

    def hasDividends(self):
        return self.hadDividends

#
Equity = AssetClass("equity", 0.003, 0)
ETC = AssetClass("ETC", 0.003, 0)
Currency = AssetClass("currency", 0, 0)


class Asset:
    def __init__(self, assetType: AssetClass, name: str, symbol: str, market: str, currency: str, quantity: int = 0,
                 avg_buy_price: float = 0,
                 avg_buy_curr_chg: float = 0,
                 last_market_value: float = 0) -> object:
        self.assetType = assetType
        self.name = name
        self.symbol = symbol
        self.market = market
        self.currency = currency
        self.quantity = quantity
        self.avg_buy_price = avg_buy_price  # this is in the actual asset currency
        self.avg_buy_curr_chg = avg_buy_curr_chg  # this is the average exchange from asset curr. to a default one (EURO)
        self.last_market_value = last_market_value


Portfolio = []

Portfolio.append(Asset(Equity, "Amplifon", "AMP.MI", "MTA", "EUR"))
Portfolio.append(Asset(Equity, "Microfocus", "MCRO.L", "LSE", "GBP"))
Portfolio.append(Asset(Currency, "GBP", "GBPEUR", "FX", "GBP"))

# First day
start_date = '2019-04-01'
# Last day
end_date = '2019-06-06'
# Call the function DataReader from the class data
amp_data = data.DataReader('AMP.MI', 'yahoo', start_date, end_date)
data = data.DataReader('GBPEUR=X', 'yahoo', start_date, end_date)
# amp_div = data.DataReader('AMP.MI', 'yahoo-dividends', start_date, end_date) #necessario trovare DataReader per Dividendi

import pandas as pd

# pd.set_printoptions(max_colwidth, 1000)
pd.set_option('display.width', 1000)

print(amp_data)
print(data)
