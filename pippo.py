# loading the class data from the package pandas_datareader
from pandas_datareader import data
# setting up Logging
import pandas as pd

pd.set_option('display.width', 1000)
import logging

logging.basicConfig(filename='backtrace.log', level=logging.DEBUG)


# Defining Basic Classes

# I need a container to track all the characteristics of a specific asset class, e.g. different commissions, dividends.
class AssetClass:
    def __init__(self, asset_type: str, buy_commission: float, annual_fee: float) -> object:
        """
        :type asset_type: str
        :type annual_fee: float
        :type buy_commission: float
        """
        # Asset Classes that I focus on
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

    def hasDividends(self):
        return self.hadDividends

    def __str__(self):
        return self.assetType


# I create the asset classes I want in my Portfolio for now
Equity = AssetClass("equity", 0.005, 0)
ETC = AssetClass("ETC", 0.005, 0)
Currency = AssetClass("currency", 0.001, 0)


# I define the concept of Asset
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

    def __str__(self):
        # return self.symbol + "\t" + self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)
        return self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)


# A Portfolio is a set of Assets that I want to access by Symbol
Portfolio = dict()

# Prima di tutto le valute di mio interesse:
Portfolio["EUR"] = Asset(Currency, "EUR", "EUREUR=X", "FX", "GBP")
Portfolio["USD"] = Asset(Currency, "USD", "USDEUR=X", "FX", "GBP")
Portfolio["GBP"] = Asset(Currency, "GBP", "GBPEUR=X", "FX", "GBP")
Portfolio["CHF"] = Asset(Currency, "CHF", "CHFEUR=X", "FX", "GBP")

# setto un patrimonio iniziale per ciascuna valuta
# simulerò strategie anche sulle valute ad una prossima iterazione
Portfolio["EUR"].quantity = 100000
Portfolio["USD"].quantity = 100000
Portfolio["GBP"].quantity = 100000
Portfolio["CHF"].quantity = 100000

# Aggiungo un ETC su Oro come elemento di diversificazione
Portfolio["PHAU.MI"] = Asset(ETC, "GOLD/WISDOMTREE", "PHAU.MI", "MTA", "EUR")

# Titoli US da me selezionati
Portfolio["DOCU"] = Asset(Equity, "DOCUSIGN", "DOCU", "NASDAQ", "USD")
Portfolio["EQIX"] = Asset(Equity, "EQUINIX REIT", "EQIX", "NASDAQ", "USD")
Portfolio["GOOG"] = Asset(Equity, "ALPHAB RG-C-NV", "GOOG", "NASDAQ", "USD")
Portfolio["GOOGL"] = Asset(Equity, "ALPHABET-A", "GOOGL", "NASDAQ", "USD")
Portfolio["MSFT"] = Asset(Equity, "MICROSOFT", "MSFT", "NASDAQ", "USD")
Portfolio["NVDA"] = Asset(Equity, "NVIDIA", "NVDA", "NASDAQ", "USD")
Portfolio["CRM"] = Asset(Equity, "SALESFORCE.COM", "CRM", "NYSE", "USD")
Portfolio["IBM"] = Asset(Equity, "IBM", "IBM", "NYSE", "USD")
Portfolio["NOW"] = Asset(Equity, "SERVICENOW", "NOW", "NYSE", "USD")
Portfolio["TWLO"] = Asset(Equity, "TWILIO-A", "TWLO", "NYSE", "USD")

# Titolo CH da me selezionati
Portfolio["ALC.SW"] = Asset(Equity, "ALCON N", "ALC.SW", "VIRTX", "CHF")
Portfolio["NOVN.SW"] = Asset(Equity, "NOVARTIS N", "NOVN.SW", "VIRTX", "CHF")
Portfolio["SOON.SW"] = Asset(Equity, "SONOVA HLDG N", "SOON.SW", "VIRTX", "CHF")

# Titoli GBP da me selezionati
Portfolio["BA.L"] = Asset(Equity, "BAE SYSTEMS", "BA.L", "LSE", "GBP")
Portfolio["BP.L"] = Asset(Equity, "BP", "BP.L", "LSE", "GBP")
Portfolio["BT-A.L"] = Asset(Equity, "BT GROUP", "BT-A.L", "LSE", "GBP")
Portfolio["ESNT.L"] = Asset(Equity, "ESSENTRA", "ESNT.L", "LSE", "GBP")
Portfolio["GLEN.L"] = Asset(Equity, "GLENCORE", "GLEN.L", "LSE", "GBP")
Portfolio["GSK.L"] = Asset(Equity, "GLAXOSMITHKLINE", "GSK.L", "LSE", "GBP")
Portfolio["HSBA.L"] = Asset(Equity, "HSBC HLDG", "HSBA.L", "LSE", "GBP")
Portfolio["KAZ.L"] = Asset(Equity, "KAZ MINERALS", "KAZ.L", "LSE", "GBP")
Portfolio["LLOY.L"] = Asset(Equity, "LLOYDS BANKING G", "LLOY.L", "LSE", "GBP")
Portfolio["MCRO.L"] = Asset(Equity, "MICRO FOCUS INTL", "MCRO.L", "LSE", "GBP")
Portfolio["RSW.L"] = Asset(Equity, "RENISHAW", "RSW.L", "LSE", "GBP")
Portfolio["RWI.L"] = Asset(Equity, "RENEWI", "RWI.L", "LSE", "GBP")
Portfolio["ULVR.L"] = Asset(Equity, "UNILEVER", "ULVR.L", "LSE", "GBP")

# Titoli EUR da me selezionati
Portfolio["AMP.MI"] = Asset(Equity, "Amplifon", "AMP.MI", "MTA", "EUR")
Portfolio["BRE.MI"] = Asset(Equity, "BREMBO", "BRE.MI", "MTA", "EUR")
Portfolio["CERV.MI"] = Asset(Equity, "CERVED GROUP", "CERV.MI", "MTA", "EUR")
Portfolio["DIA.MI"] = Asset(Equity, "DIASORIN", "DIA.MI", "MTA", "EUR")
Portfolio["ENEL.MI"] = Asset(Equity, "ENEL", "ENEL.MI", "MTA", "EUR")
Portfolio["ENI.MI"] = Asset(Equity, "ENI", "ENI.MI", "MTA", "EUR")
Portfolio["GEO.MI"] = Asset(Equity, "GEO", "GEO.MI", "MTA", "EUR")
Portfolio["MONC.MI"] = Asset(Equity, "MONCLER", "MONC.MI", "MTA", "EUR")
Portfolio["UCG.MI"] = Asset(Equity, "UNICREDIT", "UCG.MI", "MTA", "EUR")
Portfolio["0OMK.IL"] = Asset(Equity, "ESSILOR INTERNAT", "0OMK.IL", "EQUIDUCT", "EUR")
Portfolio["FME.DE"] = Asset(Equity, "FRESENIUS MEDICAL", "FME.DE", "EQUIDUCT", "EUR")
Portfolio["VNA.DE"] = Asset(Equity, "VONOVIA", "VNA.DE", "XETRA", "EUR")

# First day
start_date = '2019-06-01'
# Last day
end_date = '2019-06-06'

# get Quotations & Dividends
quotations = pd.DataFrame()
dividends = pd.DataFrame()
exchange_rates = pd.DataFrame()
for key, value in sorted(Portfolio.items()):
    assert isinstance(value, Asset)
    print("Now processing:\t" + str(key) + "\t" + str(value))
    if value.assetType.assetType != "currency":
        logging.info("is not currency");
        quotations = quotations.append(data.DataReader(str(key), "yahoo", start_date, end_date), ignore_index=True)
    elif str(str(key)) != "EUR":
        logging.info("is not EUR");
        exchange_rates = exchange_rates.append(data.DataReader(str(value.symbol), "yahoo", start_date, end_date), ignore_index=True)
    if value.assetType.hasDividends():
        logging.info("has dividends");
        dividends = dividends.append(data.DataReader(str(key), "yahoo-dividends", start_date, end_date), ignore_index=True)
    if str(key) != str(value.symbol):
        logging.warning("warning: " + str(key) + " NOT equal to " + str(value.symbol))

# Call the function DataReader from the class data
# # data = data.DataReader('GBPEUR=X', 'yahoo', start_date, end_date)
# amp_quo = data.DataReader("AMP.MI", "yahoo", start_date, end_date)['Adj Close']

##amp_act = data.DataReader("MCRO.L", "yahoo-actions", start_date, end_date)
##amp_div = data.DataReader(all_symbols, "yahoo-dividends", start_date, end_date)
# amp_div = data.DataReader(["ENEL.MI", "MSFT"], "yahoo-dividends", start_date, end_date)
# necessario trovare DataReader per Dividendi


# pd.set_printoptions(max_colwidth, 1000)


print("quotations:")
print(quotations)
print("dividends:")
print(dividends)
print("exchange_rates")
print(exchange_rates)
print()