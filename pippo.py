# loading the class data from the package pandas_datareader
from typing import List

from pandas_datareader import data

# Asset Classes that I focus on
AssetClasses = ("equity", "ETC", "currency")
equity = 0
ETC = 1
currency = 2


class Asset:
    def __init__(self, assetType: int, name: str, symbol: str, market: str, currency: str, quantity: int = 0,
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

Portfolio.append(Asset(equity, "Amplifon", "AMP.MI", "MTA", "EUR"))
Portfolio.append(Asset(equity, "Microfocus", "MCRO.L", "LSE", "GBP"))
Portfolio.append(Asset(currency, "GBP", "GBPEUR", "FX", "GBP"))

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
