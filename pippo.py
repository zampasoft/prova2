# loading the class data from the package pandas_datareader
# nota bene, ho usato l'ultima versione di pandas_datareader per fissare un errore su yahoo split
import pandas as pd
from pandas_datareader import data as pdr
import requests_cache
import datetime
expire_after = datetime.timedelta(days=3)
session = requests_cache.CachedSession(cache_name='./data/cache', backend='sqlite', expire_after=expire_after)

# print DataFrame wide
pd.set_option('display.width', 1000)
# setting up Logging
import logging
logging.basicConfig(filename='./logs/backtrace.log', level=logging.DEBUG)



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

    def hasDividends(self):
        return self.hadDividends

    def __str__(self):
        return self.assetType


# I define the concept of Asset
class Asset:
    def __init__(self, assetType: AssetClass, name: str, symbol: str, market: str, currency: str, quantity: float = 0.0,
                 avg_buy_price: float = 0,
                 avg_buy_curr_chg: float = 0,
                 historic_quotations: pd.DataFrame = pd.DataFrame(), transactions=None) -> object:
        self.assetType = assetType
        self.name = name
        self.symbol = symbol
        self.market = market
        self.currency = currency
        self.quantity = quantity
        self.avg_buy_price = avg_buy_price  # this is in the actual asset currency
        self.avg_buy_curr_chg = avg_buy_curr_chg  # this is the average exchange from asset curr. to a default one (EURO)
        self.historic_quotations = historic_quotations

    def __str__(self):
        # return self.symbol + "\t" + self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)
        return self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)

# Una transazione può avere degli stati: pending, executed, failed
# Deve avere un verbo: BUY, SELL, DIVIDEND
# Deve avere una quantità
# Deve avere un Asset su cui viene eseguito, anche se mi genererà una loop di puntatori
# Deve avere una data in cui viene richiesto
# Deve avere un valore, nel caso di BUY o SELL è il valore della transazione complessiva in valuta dell'asset
# se il verbo è DIVIDEND, è il valore unitario del dividendo nella valuta dell'asset
# Deve avere un commento
class Transaction:
    def __init__(self, verb, asset, when, quantity = 0, value = 0.0, note="", state="pending"):
        assert isinstance(asset, Asset)
        assert isinstance(when, datetime.date)
        self.when = when
        self.asset = asset
        TxValidVerbs = ("BUY", "SELL", "DIVIDEND", "SPLIT")
        if verb in TxValidVerbs:
            self.verb = verb
        else:
            raise ValueError(str(verb) + ": Invalid action. Transaction verb must be one of: " + str(TxValidVerbs))
        TxValidStates = ("pending", "executed", "failed")
        if state in TxValidStates:
            self.state = state
        else:
            raise ValueError("Transaction state must be one of: " + TxValidStates)
        if quantity >= 0:
            self.quantity = quantity
        else:
            raise ValueError("Transaction quantity must be a positive number")
        if value >= 0.0:
            self.value = value
        else:
            raise ValueError("Transaction value must be a positive number")
        self.note = note

        
    def __str__(self):
        if self.verb == "DIVIDEND" or self.verb == "SPLIT":
            return (str(self.when) + " : " + self.verb + " " + self.asset.symbol + " " + str(self.value)) + " " + str(self.quantity)
        else:
            return (str(self.when) + " : " + self.verb + " " + str(self.quantity) + " " + self.asset.symbol)

# I create the asset classes I want in my Portfolio for now
Equity = AssetClass("equity", 0.005, 0)
ETC = AssetClass("ETC", 0.005, 0)
Currency = AssetClass("currency", 0.001, 0)

# A Portfolio is a set of Assets that I want to access by Symbol
# la dimensione storica è legata ai singoli asset.
# potrebbe avere senso definire Portfolio come classe con i seguenti metodi
# init() / Load / save () per caricare/salvare dati
# un metodo print() per visualizzare il contenuto del portafoglio
# totalValue() per calcolare il valore totale del Portafoglio in EUR
class Portfolio:
    def __init__(self):
        self.assets = dict() #elenco di asset acceduti via simbolo. un giorno capirò se abbia senso una struttura dati diversa
        self.defCurrency = "EUR" 
        self.pendingTransactions = []
        self.executedTransactions = []
    def load(self):
        # Considero titoli in 4 valute ma normalizzo tutto su EUR
        # in future evoluzioni valuerò se rendere la valuta interna parametrica
        self.assets["EUR"] = Asset(Currency, "EUR", "EUREUR=X", "FX", "EUR")
        self.assets["USD"] = Asset(Currency, "USD", "USDEUR=X", "FX", "USD")
        self.assets["GBP"] = Asset(Currency, "GBP", "GBPEUR=X", "FX", "GBP")
        self.assets["CHF"] = Asset(Currency, "CHF", "CHFEUR=X", "FX", "CHF")
        # Aggiungo un ETC su Oro come elemento di diversificazione
        self.assets["PHAU.MI"] = Asset(ETC, "GOLD/WISDOMTREE", "PHAU.MI", "MTA", "EUR")
        # Titoli US da me selezionati
        self.assets["DOCU"] = Asset(Equity, "DOCUSIGN", "DOCU", "NASDAQ", "USD")
        self.assets["EQIX"] = Asset(Equity, "EQUINIX REIT", "EQIX", "NASDAQ", "USD")
        self.assets["GOOG"] = Asset(Equity, "ALPHAB RG-C-NV", "GOOG", "NASDAQ", "USD")
        self.assets["GOOGL"] = Asset(Equity, "ALPHABET-A", "GOOGL", "NASDAQ", "USD")
        self.assets["MSFT"] = Asset(Equity, "MICROSOFT", "MSFT", "NASDAQ", "USD")
        self.assets["NVDA"] = Asset(Equity, "NVIDIA", "NVDA", "NASDAQ", "USD")
        self.assets["CRM"] = Asset(Equity, "SALESFORCE.COM", "CRM", "NYSE", "USD")
        self.assets["IBM"] = Asset(Equity, "IBM", "IBM", "NYSE", "USD")
        self.assets["NOW"] = Asset(Equity, "SERVICENOW", "NOW", "NYSE", "USD")
        self.assets["TWLO"] = Asset(Equity, "TWILIO-A", "TWLO", "NYSE", "USD")
        self.assets["PEGA"] = Asset(Equity, "Pegasystems Inc.", "PEGA", "NYSE", "USD")
        self.assets["WDAY"] = Asset(Equity, "Workday, Inc.", "WDAY", "NYSE", "USD")
        self.assets["XLNX"] = Asset(Equity, "Xilinx, Inc.", "XLNX", "NYSE", "USD")
        self.assets["SQ"] = Asset(Equity, "Square, Inc.", "SQ", "NYSE", "USD")
        self.assets["VAR"] = Asset(Equity, "Varian Medical Systems, Inc.", "VAR", "NYSE", "USD")
        self.assets["VRTX"] = Asset(Equity, "Vertex Pharmaceuticals Incorporated", "VRTX", "NYSE", "USD")
        self.assets["TEAM"] = Asset(Equity, "Atlassian Corporation Plc", "TEAM", "NYSE", "USD")

        # Titolo CH da me selezionati
        self.assets["ALC.SW"] = Asset(Equity, "ALCON N", "ALC.SW", "VIRTX", "CHF")
        self.assets["NOVN.SW"] = Asset(Equity, "NOVARTIS N", "NOVN.SW", "VIRTX", "CHF")
        self.assets["SOON.SW"] = Asset(Equity, "SONOVA HLDG N", "SOON.SW", "VIRTX", "CHF")
        self.assets["NESN.SW"] = Asset(Equity, "Nestle S.A.", "NESN.SW", "VIRTX", "CHF")
        self.assets["SREN.SW"] = Asset(Equity, "Swiss Re AG", "SREN.SW", "VIRTX", "CHF")
        self.assets["ROG.SW"] = Asset(Equity, "Roche Holding AG", "ROG.SW", "VIRTX", "CHF")

        # Titoli GBP da me selezionati
        self.assets["BA.L"] = Asset(Equity, "BAE SYSTEMS", "BA.L", "LSE", "GBP")
        self.assets["BP.L"] = Asset(Equity, "BP", "BP.L", "LSE", "GBP")
        self.assets["BT-A.L"] = Asset(Equity, "BT GROUP", "BT-A.L", "LSE", "GBP")
        self.assets["ESNT.L"] = Asset(Equity, "ESSENTRA", "ESNT.L", "LSE", "GBP")
        self.assets["GLEN.L"] = Asset(Equity, "GLENCORE", "GLEN.L", "LSE", "GBP")
        self.assets["GSK.L"] = Asset(Equity, "GLAXOSMITHKLINE", "GSK.L", "LSE", "GBP")
        self.assets["HSBA.L"] = Asset(Equity, "HSBC HLDG", "HSBA.L", "LSE", "GBP")
        self.assets["KAZ.L"] = Asset(Equity, "KAZ MINERALS", "KAZ.L", "LSE", "GBP")
        self.assets["LLOY.L"] = Asset(Equity, "LLOYDS BANKING G", "LLOY.L", "LSE", "GBP")
        self.assets["MCRO.L"] = Asset(Equity, "MICRO FOCUS INTL", "MCRO.L", "LSE", "GBP")
        self.assets["RSW.L"] = Asset(Equity, "RENISHAW", "RSW.L", "LSE", "GBP")
        self.assets["RWI.L"] = Asset(Equity, "RENEWI", "RWI.L", "LSE", "GBP")
        self.assets["ULVR.L"] = Asset(Equity, "UNILEVER", "ULVR.L", "LSE", "GBP")
        self.assets["LGEN.L"] = Asset(Equity, "Legal & General Group Plc", "LGEN.L", "LSE", "GBP")
        self.assets["LSE.L"] = Asset(Equity, "London Stock Exchange Group plc", "LSE.L", "LSE", "GBP")

        # Titoli EUR da me selezionati
        self.assets["AMP.MI"] = Asset(Equity, "Amplifon", "AMP.MI", "MTA", "EUR")
        self.assets["BRE.MI"] = Asset(Equity, "BREMBO", "BRE.MI", "MTA", "EUR")
        self.assets["CPR.MI"] = Asset(Equity, "CAMPARI", "CPR.MI", "MTA", "EUR")
        self.assets["CERV.MI"] = Asset(Equity, "CERVED GROUP", "CERV.MI", "MTA", "EUR")
        self.assets["DSY.PA"] = Asset(Equity, "Dassault Systèmes SE", "DSY.PA", "EQUIDUCT", "EUR")
        self.assets["DIA.MI"] = Asset(Equity, "DIASORIN", "DIA.MI", "MTA", "EUR")
        self.assets["ENEL.MI"] = Asset(Equity, "ENEL", "ENEL.MI", "MTA", "EUR")
        self.assets["ENI.MI"] = Asset(Equity, "ENI", "ENI.MI", "MTA", "EUR")
        self.assets["FCA.MI"] = Asset(Equity, "FCA", "FCA.MI", "MTA", "EUR")
        self.assets["GEO.MI"] = Asset(Equity, "GEO", "GEO.MI", "MTA", "EUR")
        self.assets["KER.PA"] = Asset(Equity, "Kering SA", "KER.PA", "EQUIDUCT", "EUR")
        self.assets["MONC.MI"] = Asset(Equity, "MONCLER", "MONC.MI", "MTA", "EUR")
        self.assets["UCG.MI"] = Asset(Equity, "UNICREDIT", "UCG.MI", "MTA", "EUR")
        self.assets["EL.PA"] = Asset(Equity, "EssilorLuxottica Societe anonyme", "EL.PA", "EQUIDUCT", "EUR")
        self.assets["FME.DE"] = Asset(Equity, "FRESENIUS MEDICAL", "FME.DE", "EQUIDUCT", "EUR")
        self.assets["VNA.DE"] = Asset(Equity, "VONOVIA", "VNA.DE", "XETRA", "EUR")
        self.assets["MC.PA"] = Asset(Equity, "LVMH Moët Hennessy Louis Vuitton S.E.", "MC.PA", "EQUIDUCT", "EUR")
        self.assets["VVD.F"] = Asset(Equity, "Veolia Environnement S.A.", "VVD.F", "EQUIDUCT", "EUR")


#Creo la Classe TradingStrategy
class TradingStrategy:
    #per adesso è un contenitore vuoto
    def __init__(self):
        self.boh = "mah"

#Creo la classe TradingSimulation
class TradingSimulation:
    def __init__(self, port, strat):
        self.port=port
        self.strategy=strategy
        # voglio ricevere un portafoglio iniziale che contenga tutti gli input per eseguire la simulazione
        # voglio ricevere una TradingStrategy che contenga le regole da applicare
        # restiruisco un nuovo Portafoglio elaborato con le regole
    def run(self):
        return 0


### cominciamo a lavorare ###
logging.info("******************************************************")
logging.info("*                 NEW START                          *")
logging.info("******************************************************")

# Last day
end_date = datetime.date.today()
# First day
start_date = end_date - datetime.timedelta(days=365*5)


#Create and Initialise myPortfolio
myPortfolio = Portfolio()
myPortfolio.load()

splits = []

# get Quotations & Dividends for all Assets in myPortfolio
for key, value in sorted(myPortfolio.assets.items()):
    assert isinstance(value, Asset)
    print("Now retrieving quotations for:\t" + str(key) + "\t" + str(value))
    logging.info("Now retrieving quotations for:\t" + str(key) + "\t" + str(value))
    if str(key) != str(value.symbol):
        logging.warning("warning: " + str(key) + " NOT equal to " + str(value.symbol))
    # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento recupero le quotazioni storiche
    if str(key) != myPortfolio.defCurrency:
        value.historic_quotations = pdr.DataReader(value.symbol, "yahoo", start_date, end_date, session=session)
        if value.assetType.hasDividends():
            logging.info(str(key) + " has dividends");
            try:
                # i dividendi generano transazioni sulle valute
                # devo iterare tra i dividendi e creare degli ordini speciali che devo processare alla fine.
                # Portfolio[value.currency].historic_transactions
                logging.info("Getting " + str(key) + " dividends");
                temp = pdr.DataReader(value.symbol, "yahoo-actions", start_date, end_date, session=session)
                for index,row in temp.iterrows():
                    myPortfolio.pendingTransactions.append(Transaction(row["action"], value, index, 0, row["value"]))
                    if row["action"] == "SPLIT":
                        splits.append(str(value.symbol))
            except Exception as e:
                print("Failed to get dividends for " + str(value.name) + "(" + str(key) + ")")
                logging.error("Failed to get dividends for " + str(value.name) + "(" + str(key) + ")")
                logging.exception("Unexpected error:" + str(e))

print("\nThe following Stock might have had a corporate variation: " + str(splits))

# adesso dovrei aver recuperato tutti i dati
# proviamo a visualizzare qualcosa
# print Transactions
print()

print("SPLITS: ")
for i in myPortfolio.pendingTransactions:
    assert isinstance(i, Transaction)
    if i.verb == "SPLIT":
        print("SPLIT: " + str(i))
print()
