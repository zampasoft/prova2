# ver 1.0
import copy as cp
import datetime
import logging
import typing
from typing import Dict
import arrow as ar
import pandas as pd
import requests_cache
# nota bene, ho patchato l'ultima versione di pandas_datareader per fissare un errore su yahoo split
from pandas_datareader import data as pdr
import math


# Defining Basic Classes

# I need a container to track all the characteristics of a specific asset class, e.g. different commissions, dividends.
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
        #self.avg_buy_price = avg_buy_price  # this is in the actual asset currency
        #self.avg_buy_curr_chg = avg_buy_curr_chg  # this is the average exchange from asset curr. to default one (EURO)
        self.history = history

    def __str__(self):
        # return self.symbol + "\t" + self.name + "\t" + str(self.quantity) + "\t" + str(self.assetType)
        return self.name + "\t" + str(self.assetType)


# Una transazione può avere degli stati: pending, executed, failed
# Deve avere un verbo: BUY, SELL, DIVIDEND
# Deve avere una quantità
# Deve avere un Asset su cui viene eseguito, anche se mi genererà una loop di puntatori
# Deve avere una data in cui viene richiesto
# Deve avere un valore, nel caso di BUY o SELL è il valore della transazione complessiva in valuta dell'asset
# se il verbo è DIVIDEND, è il valore unitario del dividendo nella valuta dell'asset
# Deve avere un commento
class Transaction:
    def __init__(self, verb, asset, when, quantity=0, value=0.0, note="", state="pending"):
        assert isinstance(asset, Asset)
        assert isinstance(when, datetime.date)
        self.when = when
        self.asset = asset
        tx_valid_verbs = ("BUY", "SELL", "DIVIDEND", "SPLIT")
        if verb in tx_valid_verbs:
            self.verb = verb
        else:
            raise ValueError(str(verb) + ": Invalid action. Transaction verb must be one of: " + str(tx_valid_verbs))
        tx_valid_states = ("pending", "executed", "failed")
        if state in tx_valid_states:
            self.state = state
        else:
            raise ValueError("Transaction state must be one of: " + str(tx_valid_states))
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
            return (str(self.when) + " : " + self.verb + "\t" + self.asset.symbol + "\t" + str(self.value)) + " " + str(
                self.quantity) + " " + self.state

    # credo un metodo statico che userò per ordinare gli array di trabsazioni
    @staticmethod
    def to_datetime(txt):
        assert isinstance(txt, Transaction)
        # trasformo la data in un numero e ci aggiungo 1 h per ordinare la sequenza con cui eseguire gli ordini
        # la sequenza deve essere
        # prima SPLIT, poi DIVIDEND, poi SELL e infine BUY
        verbSort = None
        if txt.verb == "SPLIT":
            verbSort = 0
        elif txt.verb == "DIVIDEND":
            verbSort = 1
        elif txt.verb == "SELL":
            verbSort = 2
        elif txt.verb == "BUY":
            verbSort = 3
        else:
            raise
        return datetime.datetime.combine(txt.when, datetime.time.min) + datetime.timedelta(minutes=verbSort)


# A Portfolio is a set of Assets that I want to access by Symbol
# la dimensione storica è legata ai singoli asset.
# Portfolio di fatto è un contenitore di dati  con i seguenti metodi
# init() / Load / save () per caricare/salvare dati
# un metodo print() per visualizzare il contenuto del portafoglio
# totalValue() per calcolare il valore totale del Portafoglio in EUR
# da qualche parte ha senso mettere il valore del Portafoglio nel tempo, da capire se inserirlo come _SELF_ asset
class Portfolio:
    pendingTransactions: Dict[datetime.date, typing.List[Transaction]]

    def __init__(self, start_date : datetime.date, end_date : datetime.date, initial_capital : float = 0.0, description="Default Portfolio"):
        self.assets = dict()
        # elenco di asset acceduti via simbolo. un giorno capirò se abbia senso una struttura dati diversa
        self.defCurrency = "EUR"
        # I need to keep somewhere a history of portfolio available liquidity and total value in Def Curr
        # no data analysis needed only plotting, but I keep using DataFrame...
        # key = datetime, data = liquidity and portfolio value in def curr (netting selling commissions)
        assert(isinstance(start_date, datetime.date))
        data = {'Date': [start_date], 'Liquidity': [initial_capital], 'NetValue': [initial_capital],
                'TotalCommissions': [0.0], 'TotalDividens': [0.0], 'TotalTaxes': [0.0]}
        temp = pd.DataFrame(data, columns=['Date', 'Liquidity', 'NetValue', 'TotalCommissions', 'TotalDividens',
                                           'TotalTaxes'])
        temp['Date'] = pd.to_datetime(temp['Date'])
        self.por_history = temp.set_index('Date')
        self.days_short = 0
        self.days_long = 0
        # TODO: valutare se spostare pendingTransactions dentro self.por_history
        self.pendingTransactions = dict()
        self.executedTransactions = []
        self.failedTransactions = []
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.description = description
        # self.total_commissions = total_commissions
        logging.debug("fill_history_gaps for Portfolio[_SELF_] e Transactions")
        last_row = self.por_history.loc[self.start_date]
        for dd in ar.Arrow.range('day', datetime.datetime.combine(self.start_date, datetime.time.min),
                                 datetime.datetime.combine(self.end_date, datetime.time.min)):
            if dd.date != self.pendingTransactions.keys():
                self.pendingTransactions[dd.date()] = []
            try:
                last_row = self.por_history.loc[dd.date()]
            except KeyError as e:
                # non esiste l'indice
                logging.debug("\tMissing Index: " + str(dd.date()) + " in port_history ")
                t = datetime.datetime.combine(dd.date(), datetime.time.min)
                self.por_history.loc[t] = last_row
            except Exception as e:
                logging.exception("Unexpected error:" + str(e))
                exit(-1)


    def loadAssetList(self):
        # TODO: questa funzione sarebbe da parametrizzare su un CSV File o simile. La parte delle valute dovrebbe
        #  essere parametrica rispetto alla valuta di default. Per adesso considero titoli in 4 valute ma normalizzo
        #  tutto su EUR in future evoluzioni valuerò se rendere la valuta interna parametrica
        if self.defCurrency == "EUR":
            self.assets["USD"] = Asset(CURRENCY, "USD", "USDEUR=X", "FX", "USD")
            self.assets["GBP"] = Asset(CURRENCY, "GBP", "GBPEUR=X", "FX", "GBP")
            self.assets["CHF"] = Asset(CURRENCY, "CHF", "CHFEUR=X", "FX", "CHF")
        else:
            raise ValueError('Default Currencies other than EUR not yet implemented')
        # Aggiungo un ETC su Oro come elemento di diversificazione
        self.assets["PHAU.MI"] = Asset(ETC, "GOLD/WISDOMTREE", "PHAU.MI", "MTA", "EUR")
        # Titoli US da me selezionati
        self.assets["DOCU"] = Asset(EQUITY, "DOCUSIGN", "DOCU", "NASDAQ", "USD")
        self.assets["EQIX"] = Asset(EQUITY, "EQUINIX REIT", "EQIX", "NASDAQ", "USD")
        self.assets["GOOG"] = Asset(EQUITY, "ALPHAB RG-C-NV", "GOOG", "NASDAQ", "USD")
        self.assets["GOOGL"] = Asset(EQUITY, "ALPHABET-A", "GOOGL", "NASDAQ", "USD")
        self.assets["MSFT"] = Asset(EQUITY, "MICROSOFT", "MSFT", "NASDAQ", "USD")
        self.assets["NVDA"] = Asset(EQUITY, "NVIDIA", "NVDA", "NASDAQ", "USD")
        self.assets["CRM"] = Asset(EQUITY, "SALESFORCE.COM", "CRM", "NYSE", "USD")
        self.assets["IBM"] = Asset(EQUITY, "IBM", "IBM", "NYSE", "USD")
        self.assets["NOW"] = Asset(EQUITY, "SERVICENOW", "NOW", "NYSE", "USD")
        self.assets["TWLO"] = Asset(EQUITY, "TWILIO-A", "TWLO", "NYSE", "USD")
        self.assets["PEGA"] = Asset(EQUITY, "Pegasystems Inc.", "PEGA", "NYSE", "USD")
        self.assets["WDAY"] = Asset(EQUITY, "Workday, Inc.", "WDAY", "NYSE", "USD")
        self.assets["XLNX"] = Asset(EQUITY, "Xilinx, Inc.", "XLNX", "NYSE", "USD")
        self.assets["SQ"] = Asset(EQUITY, "Square, Inc.", "SQ", "NYSE", "USD")
        self.assets["VAR"] = Asset(EQUITY, "Varian Medical Systems, Inc.", "VAR", "NYSE", "USD")
        self.assets["VRTX"] = Asset(EQUITY, "Vertex Pharmaceuticals Incorporated", "VRTX", "NYSE", "USD")
        self.assets["TEAM"] = Asset(EQUITY, "Atlassian Corporation Plc", "TEAM", "NYSE", "USD")
        self.assets["AMZN"] = Asset(EQUITY, "Amazon", "AMZN", "NASDAQ", "USD")
        self.assets["NFLX"] = Asset(EQUITY, "Netflix", "NFLX", "NASDAQ", "USD")
        self.assets["ZM"] = Asset(EQUITY, "Zoom", "ZM", "NASDAQ", "USD")
        self.assets["DIS"] = Asset(EQUITY, "Disney", "DIS", "NYSE", "USD")
        self.assets["DPZ"] = Asset(EQUITY, "Domino's Pizza", "DPZ", "NYSE", "USD")
        self.assets["DXCM"] = Asset(EQUITY, "DexCom, Inc.", "DXCM", "NASDAQ", "USD")
        self.assets["JAZZ"] = Asset(EQUITY, "Jazz Pharmaceuticals plc", "JAZZ", "NASDAQ", "USD")
        self.assets["MED"] = Asset(EQUITY, "Medifast, Inc.", "MED", "NYSE", "USD")
        self.assets["MRNA"] = Asset(EQUITY, "Moderna, Inc.", "MRNA", "NASDAQ", "USD")
        self.assets["AAPL"] = Asset(EQUITY, "Apple Inc.", "AAPL", "NASDAQ", "USD")
        self.assets["FB"] = Asset(EQUITY, "Facebook, Inc.", "FB", "NASDAQ", "USD")
        self.assets["DBX"] = Asset(EQUITY, "Dropbox, Inc.", "DBX", "NASDAQ", "USD")
        self.assets["AVGO"] = Asset(EQUITY, "Broadcom Inc.", "AVGO", "NASDAQ", "USD")
        self.assets["WORK"] = Asset(EQUITY, "Slack Technologies, Inc.", "WORK", "NYSE", "USD")
        self.assets["GPS"] = Asset(EQUITY, "The Gap, Inc.", "GPS", "NYSE", "USD")
        self.assets["TWTR"] = Asset(EQUITY, "Twitter, Inc.", "TWTR", "NYSE", "USD")
        self.assets["ADBE"] = Asset(EQUITY, "Adobe Inc.", "ADBE", "NASDAQ", "USD")
        self.assets["SHOP"] = Asset(EQUITY, "Shopify Inc.", "SHOP", "NYSE", "USD")
        self.assets["GRPN"] = Asset(EQUITY, "Groupon Inc.", "GRPN", "NASDAQ", "USD")
        self.assets["SVMK"] = Asset(EQUITY, "SVMK Inc.", "SVMK", "NASDAQ", "USD")
        self.assets["NET"] = Asset(EQUITY, "Cloudflare Inc.", "NET", "NYSE", "USD")
        self.assets["FIT"] = Asset(EQUITY, "Fitbit Inc.", "FIT", "NYSE", "USD")
        self.assets["IT"] = Asset(EQUITY, "Gartner Inc.", "IT", "NYSE", "USD")
        self.assets["TSLA"] = Asset(EQUITY, "Tesla Inc.", "TSLA", "NASDAQ", "USD")
        self.assets["SWBI"] = Asset(EQUITY, "Smith & Wesson Brands Inc.", "SWBI", "NASDAQ", "USD")
        self.assets["ABT"] = Asset(EQUITY, "Abbott Laboratories", "ABT", "NYSE", "USD")


        # Titolo CH da me selezionati
        self.assets["ALC.SW"] = Asset(EQUITY, "ALCON N", "ALC.SW", "VIRTX", "CHF")
        self.assets["NOVN.SW"] = Asset(EQUITY, "NOVARTIS N", "NOVN.SW", "VIRTX", "CHF")
        self.assets["SOON.SW"] = Asset(EQUITY, "SONOVA HLDG N", "SOON.SW", "VIRTX", "CHF")
        self.assets["NESN.SW"] = Asset(EQUITY, "Nestle S.A.", "NESN.SW", "VIRTX", "CHF")
        self.assets["SREN.SW"] = Asset(EQUITY, "Swiss Re AG", "SREN.SW", "VIRTX", "CHF")
        self.assets["ROG.SW"] = Asset(EQUITY, "Roche Holding AG", "ROG.SW", "VIRTX", "CHF")
        self.assets["LONN.SW"] = Asset(EQUITY, "Lonza Group Ltd", "LONN.SW", "VIRTX", "CHF")
        self.assets["GIVN.SW"] = Asset(EQUITY, "Givaudan SA", "GIVN.SW", "VIRTX", "CHF")

        # Titoli GBP da me selezionati
        self.assets["BA.L"] = Asset(EQUITY, "BAE SYSTEMS", "BA.L", "LSE", "GBP")
        self.assets["BP.L"] = Asset(EQUITY, "BP", "BP.L", "LSE", "GBP")
        self.assets["BT-A.L"] = Asset(EQUITY, "BT GROUP", "BT-A.L", "LSE", "GBP")
        #self.assets["CDM.L"] = Asset(EQUITY, "Codemasters Group", "CDM.L", "LSE", "GBP")
        self.assets["BRBY.L"] = Asset(EQUITY, "Burberry Group", "BRBY.L", "LSE", "GBP")
        self.assets["ESNT.L"] = Asset(EQUITY, "ESSENTRA", "ESNT.L", "LSE", "GBP")
        self.assets["GLEN.L"] = Asset(EQUITY, "GLENCORE", "GLEN.L", "LSE", "GBP")
        self.assets["GSK.L"] = Asset(EQUITY, "GLAXOSMITHKLINE", "GSK.L", "LSE", "GBP")
        self.assets["HSBA.L"] = Asset(EQUITY, "HSBC HLDG", "HSBA.L", "LSE", "GBP")
        self.assets["KAZ.L"] = Asset(EQUITY, "KAZ MINERALS", "KAZ.L", "LSE", "GBP")
        self.assets["LLOY.L"] = Asset(EQUITY, "LLOYDS BANKING G", "LLOY.L", "LSE", "GBP")
        self.assets["MCRO.L"] = Asset(EQUITY, "MICRO FOCUS INTL", "MCRO.L", "LSE", "GBP")
        self.assets["RSW.L"] = Asset(EQUITY, "RENISHAW", "RSW.L", "LSE", "GBP")
        self.assets["RWI.L"] = Asset(EQUITY, "RENEWI", "RWI.L", "LSE", "GBP")
        self.assets["ULVR.L"] = Asset(EQUITY, "UNILEVER", "ULVR.L", "LSE", "GBP")
        self.assets["LGEN.L"] = Asset(EQUITY, "Legal & General Group Plc", "LGEN.L", "LSE", "GBP")
        self.assets["LSE.L"] = Asset(EQUITY, "London Stock Exchange Group plc", "LSE.L", "LSE", "GBP")
        self.assets["SSE.L"] = Asset(EQUITY, "SSE plc", "SSE.L", "LSE", "GBP")
        self.assets["AV.L"] = Asset(EQUITY, "Aviva plc", "AV.L", "LSE", "GBP")
        self.assets["TSCO.L"] = Asset(EQUITY, "Tesco PLC", "TSCO.L", "LSE", "GBP")
        self.assets["MRW.L"] = Asset(EQUITY, "Wm Morrison Supermarkets PLC", "MRW.L", "LSE", "GBP")
        self.assets["OCDO.L"] = Asset(EQUITY, "Ocado Group plc", "OCDO.L", "LSE", "GBP")


        # Titoli EUR da me selezionati
        self.assets["AMP.MI"] = Asset(EQUITY, "Amplifon", "AMP.MI", "MTA", "EUR")
        self.assets["BRE.MI"] = Asset(EQUITY, "BREMBO", "BRE.MI", "MTA", "EUR")
        self.assets["CPR.MI"] = Asset(EQUITY, "CAMPARI", "CPR.MI", "MTA", "EUR")
        self.assets["G.MI"] = Asset(EQUITY, "Assicurazioni Generali", "G.MI", "MTA", "EUR")
        self.assets["CERV.MI"] = Asset(EQUITY, "CERVED GROUP", "CERV.MI", "MTA", "EUR")
        self.assets["DSY.PA"] = Asset(EQUITY, "Dassault Systèmes SE", "DSY.PA", "EQUIDUCT", "EUR")
        self.assets["DIA.MI"] = Asset(EQUITY, "DIASORIN", "DIA.MI", "MTA", "EUR")
        self.assets["ENEL.MI"] = Asset(EQUITY, "ENEL", "ENEL.MI", "MTA", "EUR")
        self.assets["ENI.MI"] = Asset(EQUITY, "ENI", "ENI.MI", "MTA", "EUR")
        self.assets["FCA.MI"] = Asset(EQUITY, "FCA", "FCA.MI", "MTA", "EUR")
        self.assets["GEO.MI"] = Asset(EQUITY, "GEO", "GEO.MI", "MTA", "EUR")
        self.assets["NEXI.MI"] = Asset(EQUITY, "Nexi S.p.A.", "NEXI.MI", "MTA", "EUR")
        self.assets["STM.MI"] = Asset(EQUITY, "STMicroelectronics N.V.", "STM.MI", "MTA", "EUR")
        self.assets["PST.MI"] = Asset(EQUITY, "Poste Italiane SpA", "PST.MI", "MTA", "EUR")
        self.assets["KER.PA"] = Asset(EQUITY, "Kering SA", "KER.PA", "EQUIDUCT", "EUR")
        self.assets["MONC.MI"] = Asset(EQUITY, "MONCLER", "MONC.MI", "MTA", "EUR")
        self.assets["UCG.MI"] = Asset(EQUITY, "UNICREDIT", "UCG.MI", "MTA", "EUR")
        self.assets["EL.PA"] = Asset(EQUITY, "EssilorLuxottica Societe anonyme", "EL.PA", "EQUIDUCT", "EUR")
        self.assets["FME.DE"] = Asset(EQUITY, "FRESENIUS MEDICAL", "FME.DE", "EQUIDUCT", "EUR")
        self.assets["VNA.DE"] = Asset(EQUITY, "VONOVIA", "VNA.DE", "XETRA", "EUR")
        self.assets["MC.PA"] = Asset(EQUITY, "LVMH Moët Hennessy Louis Vuitton S.E.", "MC.PA", "EQUIDUCT", "EUR")
        self.assets["VVD.F"] = Asset(EQUITY, "Veolia Environnement S.A.", "VVD.F", "EQUIDUCT", "EUR")
        self.assets["ISP.MI"] = Asset(EQUITY, "Intesa Sanpaolo", "ISP.MI", "MTA", "EUR")
        self.assets["MZB.MI"] = Asset(EQUITY, "Massimo Zanetti Beverage Group", "MZB.MI", "MTA", "EUR")
        self.assets["SAP.DE"] = Asset(EQUITY, "SAP", "SAP.DE", "XETRA", "EUR")
        self.assets["ADS.DE"] = Asset(EQUITY, "Adidas AG", "ADS.DE", "XETRA", "EUR")
        self.assets["DPW.DE"] = Asset(EQUITY, "Deutsche Post AG", "DPW.DE", "XETRA", "EUR")




    def calc_stats(self, days_short=20, days_long=150):
        # TODO: questo metodo dovrebbe stare a livello di Strategia... Però deve essere eseguito prima di sistemare i
        #  gaps, quindi per il momento lo lascio a livello di portafoglio
        logging.debug("Entering calc_stats")
        self.days_short = days_short
        self.days_long = days_long
        logging.debug("Setting days_short: " + str(self.days_short))
        logging.debug("Setting days_long: " + str(self.days_long))
        # asset['SMA_short'] = 0.0
        # asset['SMA_long'] = 0.0
        # asset['STD_short'] = 0.0
        for key, asset in sorted(self.assets.items()):
            logging.debug("Processing :" + asset.symbol)
            sma_short = asset.history['Close'].rolling(window=days_short).mean()
            asset.history['sma_short'] = sma_short
            sma_long = asset.history['Close'].rolling(window=days_long).mean()
            asset.history['sma_long'] = sma_long
            std_short = asset.history['Close'].rolling(window=days_short).std()
            asset.history['std_short'] = std_short

            std_long = asset.history['Close'].rolling(window=days_long).std()
            asset.history['std_long'] = std_long
            # asset.history.plot(y=['Close', 'sma_short', 'sma_long'], title=asset.symbol)
            # plt.show()
            print(".", end="", flush=True)
        print(" ")


    # TODO: questo metodo dovrebbe essere multi-thread.
    def fill_history_gaps(self):
        logging.debug("Entering fill_history_gaps")
        for key, asset in sorted(self.assets.items()):
            print(".", end="", flush=True)
            # create a set containing all dates in Range
            logging.debug("Processing :" + asset.symbol)
            last_row = [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            if asset.symbol == self.defCurrency:
                asset.history = pd.DataFrame() # devo definire la struttura
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.start_date, datetime.time.min),
                                     datetime.datetime.combine(self.end_date, datetime.time.min)):
                try:
                    last_row = asset.history.loc[dd.date(), : ]
                    # ogni tanto le quotazioni inglesi fanno casino tra pence e pound.
                    # se il valore esiste, ma rappresenta un errore, allora lo sostituisco con la media a 20 gg
                    if asset.currency == "GBP" and not math.isnan(last_row['sma_short']):
                        # se il valore è inferiore al 2% della media corta, probabilmente hanno invertito GBP e GBp
                        if last_row['Close'] < last_row['sma_short'] * 0.02:
                            logging.info("Found Outlier: managing as GBP/GBp error for " + asset.symbol + " on " + str(dd.date()))
                            last_row['Close'] = last_row['Close'] * 100
                            # di solito se è sbagliato il close lo è anche l'Open
                            if last_row['Open'] < last_row['sma_short'] * 0.02:
                                last_row['Open'] = last_row['Open'] * 100
                except KeyError as e:
                    # non esiste l'indice
                    logging.debug("\tMissing Index: " + str(dd.date()) + " in Asset " + str(asset.symbol))
                    t = datetime.datetime.combine(dd.date(), datetime.time.min)
                    asset.history.loc[t] = last_row
                    # ho due situazioni limite: alcune azioni non esistono prima di una certa data
                    # e altre volte semplicemente pesco un festivo come primo giorno
                    # da capire
                except Exception as e:
                    logging.exception("Unexpected error:" + str(e))
                    exit(-1)
            # asset.history = asset.history.sort_index()
            # estendo il DataFrame aggiungendo la colonna OwnedAmount
            asset.history['OwnedAmount'] = 0.0
            asset.history['AverageBuyPrice'] = 0.0 # in DEF CURR
            asset.history['NetWorth'] = 0.0 # in DEF CURR
            asset.history['TotTaxes'] = 0.0  # in DEF CURR
            asset.history['TotCommissions'] = 0.0  # in DEF CURR
        print(" ")



    def port_net_value(self, date: datetime.datetime):
        tot_value = 0.0
        GBPEUR = self.assets['GBP'].history.loc[date]['Close']/100 # quotazioni e dividendi UK sono in pence
        CHFEUR = self.assets['CHF'].history.loc[date]['Close']
        USDEUR = self.assets['USD'].history.loc[date]['Close']
        for key, asset in self.assets.items():
            line = asset.history.loc[date]
            if line['OwnedAmount'] > 0.0:
                curr_conv = 1.0
                if asset.currency != "EUR":
                    if asset.currency == "USD":
                        curr_conv = USDEUR
                    elif asset.currency == "GBP":
                        curr_conv = GBPEUR
                    elif asset.currency == "CHF":
                        curr_conv = CHFEUR
                logging.debug("Calculating Port Net Value")
                logging.debug("Asset: " + asset.symbol)
                logging.debug("Owned Amount: " + str(line['OwnedAmount']))
                logging.debug("Average Buy_Price: " + str(line['AverageBuyPrice']))
                logging.debug("Currency Conversion: " + str(curr_conv))
                logging.debug("current quotation: " + str(line['Close']))
                # TODO: aggiungere NerWorth anche su singolo asset, per permettere regole di bilanciamento del portafoglio
                line['NetWorth'] = line['OwnedAmount'] * (line['Close']*curr_conv + asset.assetType.tax_rate*(line['AverageBuyPrice'] - line['Close']*curr_conv ))
                tot_value = tot_value + line['NetWorth']
                # FIXME: con questa formula, in caso di perdita, lo zainetto fiscale mi fa aumentare leggermente il valore
                # manca la SELL commission, ma incide poco sul senso del numero
        logging.debug("calcolato tot_value per giorno: " + str(date))
        self.por_history.loc[date]['NetValue'] = self.por_history.loc[date]['Liquidity'] + tot_value # da finire


    def loadQuotations(self, cache_file = 'cache'):
        # setto una cache per i pandas_datareader
        # TODO: dovrei rendere la location e la durata della cache parametriche
        expire_after = datetime.timedelta(days=3)
        session = requests_cache.CachedSession(cache_name=cache_file, backend='sqlite', expire_after=expire_after, allowable_codes=(200, ), fast_save=True)
        # get Quotations & Dividends for all Assets in myPortfolio
        for key, value in sorted(self.assets.items()):
            print(".", end="", flush=True)
            assert isinstance(value, Asset)
            logging.info("Now retrieving quotations for:\t" + str(key) + "\t" + str(value))
            if str(key) != str(value.symbol):
                logging.warning("warning: " + str(key) + " NOT equal to " + str(value.symbol))
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento recupero
            # le quotazioni storiche
            if str(key) != self.defCurrency:
                value.history = pdr.DataReader(value.symbol, "yahoo", self.start_date, self.end_date,
                                                           session=session)
                logging.debug("number of objects retrieved: " + str(value.history.size) + " for " + value.symbol)
                if value.assetType.hasDividends():
                    logging.debug("\t" + str(key) + " has dividends")
                    try:
                        # i dividendi generano transazioni sulle valute
                        # devo iterare tra i dividendi e creare degli ordini speciali che devo processare alla fine.
                        # Portfolio[value.currency].historic_transactions
                        logging.info("\tGetting " + str(key) + " dividends")
                        temp = pdr.DataReader(value.symbol, "yahoo-actions", self.start_date, self.end_date,
                                              session=session)

                        for index, row in temp.iterrows():
                            self.pendingTransactions[index.date()].append(
                                Transaction(row["action"], value, index.date(), 0, row["value"]))
                    except Exception as e:
                        logging.error("Failed to get dividends for " + str(value.name) + "(" + str(key) + ")")
                        logging.exception("Unexpected error:" + str(e))
                        exit(-1)
        print(" ")

    def printReport(self):
        print("Portafoglio: " + str(self.description))
        # print("Initial Value:\n" + str(self.por_history.loc[self.start_date]))
        print("Final Value:\n" + str(self.por_history.loc[self.end_date]))


# Creo la Classe TradingStrategy
# analizza il portafoglio un asset alla volta.
# Se voglio imporre vincoli tra asset, lo faccio all'interno della Simulazione
# ad esempio ETC oro deve essere tra 5% e 10% del valore totale del Portafoglio
# Devo avere valuta per investire, etc...
# come strategia di Trading Baseline, implemento BUY&HOLD
# se voglio fare strategie più sofisticate eredito e faccio override del metodo 'suggested_transactions'
# ricordarsi di aggiungere StopLossTreshold (10%?)
class BuyAndHoldTradingStrategy:
    def __init__(self, in_port: Portfolio):
        self.description = "BUY and HOLD"
        # clono il Portafoglio in Input così lo posso modificare
        self.outcome = cp.deepcopy(in_port)
        self.outcome.description = self.description
        # setto un valore standard per i BUY oders, in modo che sia possibile investire su tutti gli asset
        #self.BUY_ORDER_VALUE = self.outcome.initial_capital / len(self.outcome.assets.keys())
        self.BUY_ORDER_VALUE = 0
        # voglio ricevere un portafoglio iniziale che contenga tutti gli input per eseguire la simulazione
        # voglio ricevere una TradingStrategy che contenga le regole da applicare
        # restiruisco un nuovo Portafoglio elaborato con le regole

    # TODO: questo metodo dovrebbe essere multi-thread.
    def calc_suggested_transactions(self, sell_all=True, **kwparams):
        # Strategia base "BUY & HOLD"
        # wish_list = ["IBM", "GLEN.L", "MCRO.L", "MSFT", "GOOG", "GOOGL", "KAZ.L", "BRE.MI", "CRM", "RSW.L", "FME.DE",
        #             "ENEL.MI", "EQIX", "LLOY.L", "BP.L", "HSBA.L", "RWI.L", "SOON.SW", "BA.L", "PHAU.MI", "UCG.MI",
        #             "GSK.L", "TWLO", "ESNT.L", "BT-A.L", "GEO.MI", "ENI.MI", "NOVN.SW"]
        wish_list = ["ENEL.MI", "PHAU.MI", "NEXI.MI", "DPW.DE", "FME.DE", "KER.PA", "AV.L", "LSE.L", "RSW.L", "TEAM", "SWBI", "SVMK", "MED", "NOW", "WORK", "DIS", "VNA.DE"]
        days_long = self.outcome.days_long
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            if asset.symbol in wish_list:
                for dd in ar.Arrow.range('week', datetime.datetime.combine(self.outcome.start_date, datetime.time.min) + datetime.timedelta(days=days_long),
                                             datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1), datetime.time.min)):
                    if asset.history.loc[dd.date(), 'Close'] > 0.0 and asset.assetType.assetType != "currency":
                        logging.debug("\tRequesting BUY for " + str(key) + " on " + str(dd.date() +
                                                                                   datetime.timedelta(days=1)))
                        logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(Transaction("BUY", asset, dd.date() +
                                                                   datetime.timedelta(days=1), 0, 0.0, self.description))
                        wish_list.remove(asset.symbol)
                        break
            print(".", end="", flush=True)
            # l'ultimo giorno vendo tutto.
            if sell_all:
            # l'ultimo giorno vendo tutto.
                if asset.assetType.assetType != "currency":
                    logging.info("\tRequesting SELL for " + str(key) + " on " + str(self.outcome.end_date))
                    dailyPendTx = self.outcome.pendingTransactions[self.outcome.end_date]
                    dailyPendTx.append(Transaction("SELL", asset, self.outcome.end_date, 0, 0.0, self.description))
        print(" ")
        return self.outcome.pendingTransactions

    # Creo il metodo TradingSimulation che deve iterare dentro un range di date, eseguire gli ordini e aggiornare i valori
    def runTradingSimulation(self, max_orders = 25.0):
        logging.debug("Processing portfolio \'{0}\' start_date = {1} end_date = {2}".format(self.outcome.description,
                                                                                            str(self.outcome.start_date),
                                                                                            str(self.outcome.end_date)))
        self.BUY_ORDER_VALUE = self.outcome.initial_capital / max_orders
        # max_orders = rappresenta una stima del numero massimo di ordini eseguiti in un BUY & HOLD.
        # con strategie più complesse, è una indicazione spannometrica del numero di titoli massimo nel portafoglio
        logging.info("\nSetting BUY order value to: " + str(self.BUY_ORDER_VALUE))
        # prima di tutto comincio a stampare la lista della transazioni pending
        #for key, value in self.outcome.pendingTransactions.items():
        #    print ("Key: " + str(key))
        #    for tx in value:
        #        print(" Tx: " + str(tx))
        # self.outcome.pendingTransactions.sort(reverse=False, key=Transaction.to_datetime)
        # il trading parte da start_date + 1 gg, prima non posso avere ordini basati su nessun dato
        first_trading_day = self.outcome.start_date + datetime.timedelta(days=1)
        # inizializzo un paio di variabili che utilizzo per stampre un'idea di progress bar
        count = 0
        mod = len(self.outcome.por_history) -1
        # inizio a fare il vero trading
        for dd in ar.Arrow.range('day', datetime.datetime.combine(first_trading_day, datetime.time.min),
                                datetime.datetime.combine(self.outcome.end_date, datetime.time.min)):
            logging.debug("\tProcessing Trading Day " + str(dd.date()))
            # dovrei iterare sui giorni ed eseguire le transazioni
            # prima di tutto copio i valori por_history e asset history da ieri
            # prima di tutto, passo tutti gli asset e se amount è > 0 calcolo il CLOSE_PRICE in EUR
            # mi serve un metodo per calcolare il valore del Port in un dato giorno.
            # ... devo riempire tutti i giorni per ...
            # ...
            # assumo
            prev_day = dd.date() - datetime.timedelta(days=1)
            # copio port history
            self.outcome.por_history.loc[dd.date()] = self.outcome.por_history.loc[prev_day]
            # processo gli asset
            for sym, asset in self.outcome.assets.items():
                count += 1
                if count % mod == 0:
                    print(".", end="", flush=True)
                # propago i cambiamenti del giorno precedente
                asset.history.loc[dd.date()]['OwnedAmount'] = asset.history.loc[prev_day]['OwnedAmount']
                asset.history.loc[dd.date()]['AverageBuyPrice'] = asset.history.loc[prev_day]['AverageBuyPrice']
            today_tx = []
            try:
                #today_tx = self.outcome.pendingTransactions[datetime.datetime.combine(r.date(), datetime.time.min)]
                today_tx = self.outcome.pendingTransactions[dd.date()]
                today_tx.sort(reverse=False, key=Transaction.to_datetime)
            except KeyError as ke:
                logging.exception(ke)
                logging.debug("No pending TX for day: " + str(dd.date))
            if len(today_tx) > 0:
                for t in today_tx:
                    self.exec_trade(t)
            # calcolo il valore netto di Portafoglio alla fine della giornata di Trading.
            self.outcome.port_net_value(dd.date())
            # ricalcolo order value come percentuale del net value
            self.BUY_ORDER_VALUE = self.outcome.por_history.loc[dd.date()]['NetValue'] / max_orders
        print("\nBella zio!")
        return self.outcome


    def exec_trade(self, t : Transaction):
        # TODO: spostare order value come parametro di questo metodo, che è l'unico posto in cui viene usato
        # TODO: verificare che lo stato della Transazione sia Pending
        # recupero l'asset su cui devo operare
        logging.debug("Executing transaction: " + str(t))
        asset = self.outcome.assets[t.asset.symbol]

        #recupero il fattore di conversione per la valuta
        GBPEUR = self.outcome.assets['GBP'].history.loc[t.when]['Open'] / 100.0
        CHFEUR = self.outcome.assets['CHF'].history.loc[t.when]['Open']
        USDEUR = self.outcome.assets['USD'].history.loc[t.when]['Open']

        curr_conv = 1.0
        if asset.currency != "EUR":
            if asset.currency == "USD":
                curr_conv = USDEUR
            elif asset.currency == "GBP":
                curr_conv = GBPEUR
            elif asset.currency == "CHF":
                curr_conv = CHFEUR
        logging.debug(asset.currency + " curr_conv " + str(curr_conv))

        if t.verb == "BUY":
            logging.debug("Buying " + str(t))
            # TODO: improve Buying Quantity calculation...

            #  assumo di eseguire gli ordini di BUY e SELL come prima
            #  azione della giornata, avendoli calcolati la sera del giorno prima
            logging.debug("asset price " + str(asset.history.loc[t.when]['Open']))
            quantity = math.floor(self.BUY_ORDER_VALUE / (asset.history.loc[t.when]['Open']*curr_conv))
            asset_price = quantity * asset.history.loc[t.when]['Open'] * curr_conv
            commission = asset_price * asset.assetType.buyCommission
            if self.outcome.por_history.loc[t.when]['Liquidity'] >= (asset_price + commission) and quantity > 0.0:
                # eseguo tx
                # diminuisco liquidità
                self.outcome.por_history.loc[t.when]['Liquidity'] -= (asset_price + commission)
                # aumento il monte commissioni
                self.outcome.por_history.loc[t.when]['TotalCommissions'] += commission
                # modifico average buy price
                asset.history.loc[t.when]['AverageBuyPrice'] = (asset.history.loc[t.when]['OwnedAmount']*asset.history.loc[t.when]['AverageBuyPrice'] + asset_price)/(asset.history.loc[t.when]['OwnedAmount'] + quantity)
                # aumento quantità posseduta
                asset.history.loc[t.when]['OwnedAmount'] += quantity
                t.state = "executed"
                t.quantity = quantity
                t.value = asset_price
                logging.info("Tx " + str(t) + "\tvalue: " + str(asset_price))
                self.outcome.executedTransactions.append(t)
            else:
                # tx fallita per mancanza di liquidità
                t.state = "failed"
                t.note += "Not enough liquidity. Transaction" + str(t) + " failed."
                logging.debug("Tx failed, Not enough liquidity. (Avail. Liquidity: " + str(self.outcome.por_history.loc[t.when]['Liquidity']) + ")")
                self.outcome.failedTransactions.append(t)
        elif t.verb == "SELL":
            logging.debug("Selling " + str(t))
            if asset.history.loc[t.when]['OwnedAmount'] > 0.0:
                # vendo
                quantity = asset.history.loc[t.when]['OwnedAmount']
                asset_price = quantity * asset.history.loc[t.when]['Open'] * curr_conv
                commission = asset_price * asset.assetType.buyCommission
                asset.history.loc[t.when]['OwnedAmount'] = 0.0
                # calcolo le tasse
                tax = (asset_price - quantity * asset.history.loc[t.when]['AverageBuyPrice']) * asset.assetType.tax_rate
                #aggiorno liquidità
                self.outcome.por_history.loc[t.when]['Liquidity'] += (asset_price - commission - tax)
                # aumento il monte commissioni
                self.outcome.por_history.loc[t.when]['TotalCommissions'] += commission
                # aggiorno le tasse totali
                self.outcome.por_history.loc[t.when]['TotalTaxes'] += tax
                # FIXME: devo aggiornare le tasse su ciascuna azione
                t.state = "executed"
                t.quantity = quantity
                t.value = asset_price
                logging.info("Tx " + str(t) + "\tvalue: " + str(asset_price))
                self.outcome.executedTransactions.append(t)
            else:
                t.state = "failed"
                t.note += "Nothing to SELL. Transaction" + str(t) + " failed."
                logging.debug("Tx failed, Nothing to SELL")
                self.outcome.failedTransactions.append(t)
        elif t.verb == "DIVIDEND":
            logging.debug("DVND " + str(t))
            tax = asset.assetType.tax_rate * curr_conv * asset.history.loc[t.when]['OwnedAmount'] * t.value
            logging.debug("TAX: " + str(tax))
            net_divd = asset.history.loc[t.when]['OwnedAmount'] * t.value * curr_conv * (1 - asset.assetType.tax_rate)
            logging.debug("Net dividend: " + str(net_divd))
            self.outcome.por_history.loc[t.when]['Liquidity'] += net_divd
            t.state = "executed"
            # aggiorno le tasse totali
            self.outcome.por_history.loc[t.when]['TotalTaxes'] += tax
            t.quantity = asset.history.loc[t.when]['OwnedAmount']
            self.outcome.por_history.loc[t.when]['TotalDividens'] += net_divd
            self.outcome.executedTransactions.append(t)
            logging.debug("Dividend from " + str(asset.symbol) + " tot Value: " + str(asset.history.loc[t.when]['OwnedAmount'] * t.value * curr_conv * (1 - asset.assetType.tax_rate)))
        else:
            logging.debug("Ignoring Tx: " + str(t))
            t.state = "failed"
            t.note += " - no instructions for VERB: " + t.verb
            self.outcome.failedTransactions.append(t)
        # TODO: rimuovere transazione da pendingTransactions


# Per definire una strategia più complessa estendo la classe BuyAndHoldTradingStrategy e faccio overload del metodo
# che calcola le suggested transactions
# questa strategia funziona bene in mercati trending
class InvBollbandsStrategy(BuyAndHoldTradingStrategy):

    def __init__(self, in_port):
        super().__init__(in_port)
        self.description = "Inverse Bollinger Bands"
        self.outcome.description = self.description

    def calc_suggested_transactions(self, sell_all=True, initial_buy=True, w_short=1.0, w_long=1.0):
        # Estendo la strategia base "BUY & HOLD"
        # per confrontare mele con mele, partirei sempre dal Buy and Hold
        if initial_buy:
            super().calc_suggested_transactions(sell_all=False)
        # w_short e w_long sono i moltiplicatori delle banda di Bollingher short e long
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            days_short = self.outcome.days_short
            days_long = self.outcome.days_long
            boll_multi = w_long
            days_buy = []
            quot_buy = []
            days_sell = []
            quot_sell = []
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.outcome.start_date, datetime.time.min) + datetime.timedelta(days=days_long),
                                         datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1),
                                                                   datetime.time.min)):
                # mi assicuro che esistano quotazioni per l'asset, che non sia una valuta e che la varianza sia
                # significativa, altrimenti siamo in una fase di spostamento laterale
                if asset.history.loc[dd.date(), 'Close'] > 0.0 and asset.assetType.assetType != "currency" and asset.history.loc[dd.date(), 'std_short'] > 0.03 * asset.history.loc[dd.date(), 'sma_short']:

                    prev_day = dd.date() - datetime.timedelta(days=1)
                    boll_up_old = asset.history.loc[prev_day, 'sma_long'] + boll_multi * asset.history.loc[prev_day, 'std_long']
                    boll_down_old = asset.history.loc[prev_day, 'sma_long'] - boll_multi * asset.history.loc[prev_day, 'std_long']
                    quot_old = asset.history.loc[prev_day, 'Close']
                    quot = asset.history.loc[dd.date(), 'Close']
                    boll_up = asset.history.loc[dd.date(), 'sma_long'] + boll_multi * asset.history.loc[dd.date(), 'std_long']
                    boll_down = asset.history.loc[dd.date(), 'sma_long'] - boll_multi * asset.history.loc[dd.date(), 'std_long']
                    sma_long = asset.history.loc[dd.date(), 'sma_long']
                    sma_long_old = asset.history.loc[prev_day, 'sma_long']

                    if quot > boll_up and quot_old < boll_up_old:
                        # BUY
                        reason = "TRENDING UP"
                        logging.debug("\t" + reason + ": Requesting BUY for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']))
                        logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(
                            Transaction("BUY", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                  reason))
                        days_buy.append(dd.date())
                        quot_buy.append(quot)
                    elif quot < boll_down and quot_old > boll_down_old:
                        #SELL
                        reason = "TRENDING DOWN"
                        logging.debug("\t" + reason + ": Requesting SELL for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(
                            asset.history.loc[dd.date(), 'Close']))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0, reason))
                        days_sell.append(dd.date())
                        quot_sell.append(quot)
            print(".", end="", flush=True)
            # BUY_points = pd.DataFrame({'Date': days_buy, 'Quotation': quot_buy})
            # SELL_points = pd.DataFrame({'Date': days_sell, 'Quotation': quot_sell})
            # ax = asset.history['Close'].plot(title=asset.symbol)
            # BUY_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="green", alpha=0.5)
            # SELL_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="red", alpha=0.5)
            # plt.show()
            if sell_all:
            # l'ultimo giorno vendo tutto.
             if asset.assetType.assetType != "currency":
                logging.info("\tRequesting SELL for " + str(key) + " on " + str(self.outcome.end_date))
                dailyPendTx = self.outcome.pendingTransactions[self.outcome.end_date]
                dailyPendTx.append(Transaction("SELL", asset, self.outcome.end_date, 0, 0.0, self.description))
        print(" ")
        return self.outcome.pendingTransactions


# Per definire una strategia più complessa estendo la classe BuyAndHoldTradingStrategy e faccio overload del metodo
# che calcola le suggested transactions
# questa strategia funziona bene in mercati bounded
class BollbandsStrategy(BuyAndHoldTradingStrategy):

    def __init__(self, in_port):
        super().__init__(in_port)
        self.description = "Bollinger Bands"
        self.outcome.description = self.description

    def calc_suggested_transactions(self, sell_all=True, initial_buy=True, w_short=1.0, w_long=1.0):
        # Estendo la strategia base "BUY & HOLD"
        # per confrontare mele con mele, partirei sempre dal Buy and Hold
        if initial_buy:
            super().calc_suggested_transactions(sell_all=False)
        # w_short e w_long sono i moltiplicatori delle banda di Bollingher short e long
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            days_short = self.outcome.days_short
            days_long = self.outcome.days_long
            boll_multi = w_long
            days_buy = []
            quot_buy = []
            days_sell = []
            quot_sell = []
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.outcome.start_date, datetime.time.min) + datetime.timedelta(days=days_long),
                                         datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1),
                                                                   datetime.time.min)):
                # mi assicuro che esistano quotazioni per l'asset, che non sia una valuta e che la varianza sia
                # significativa, altrimenti siamo in una fase di spostamento laterale
                if asset.history.loc[dd.date(), 'Close'] > 0.0 and asset.assetType.assetType != "currency" and asset.history.loc[dd.date(), 'std_short'] > 0.03 * asset.history.loc[dd.date(), 'sma_short']:

                    prev_day = dd.date() - datetime.timedelta(days=1)
                    boll_up_old = asset.history.loc[prev_day, 'sma_long'] + boll_multi * asset.history.loc[prev_day, 'std_long']
                    boll_down_old = asset.history.loc[prev_day, 'sma_long'] - boll_multi * asset.history.loc[prev_day, 'std_long']
                    quot_old = asset.history.loc[prev_day, 'Close']
                    quot = asset.history.loc[dd.date(), 'Close']
                    boll_up = asset.history.loc[dd.date(), 'sma_long'] + boll_multi * asset.history.loc[dd.date(), 'std_long']
                    boll_down = asset.history.loc[dd.date(), 'sma_long'] - boll_multi * asset.history.loc[dd.date(), 'std_long']
                    sma_long = asset.history.loc[dd.date(), 'sma_long']
                    sma_long_old = asset.history.loc[prev_day, 'sma_long']

                    if quot > boll_down and quot_old < boll_down_old:
                        # BUY
                        reason = "CHEAP"
                        logging.debug("\t" + reason + ": Requesting BUY for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']))
                        logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(
                            Transaction("BUY", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                  reason))
                        days_buy.append(dd.date())
                        quot_buy.append(quot)
                    elif quot < boll_up and quot_old > boll_up_old:
                        #SELL
                        reason = "EXPENSIVE"
                        logging.debug("\t" + reason + ": Requesting SELL for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(
                            asset.history.loc[dd.date(), 'Close']))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0, reason))
                        days_sell.append(dd.date())
                        quot_sell.append(quot)
            print(".", end="", flush=True)
            # BUY_points = pd.DataFrame({'Date': days_buy, 'Quotation': quot_buy})
            # SELL_points = pd.DataFrame({'Date': days_sell, 'Quotation': quot_sell})
            # ax = asset.history['Close'].plot(title=asset.symbol)
            # BUY_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="green", alpha=0.5)
            # SELL_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="red", alpha=0.5)
            # plt.show()
            if sell_all:
                # l'ultimo giorno vendo tutto.
                if asset.assetType.assetType != "currency":
                    logging.info("\tRequesting SELL for " + str(key) + " on " + str(self.outcome.end_date))
                    dailyPendTx = self.outcome.pendingTransactions[self.outcome.end_date]
                    dailyPendTx.append(Transaction("SELL", asset, self.outcome.end_date, 0, 0.0, self.description))
        print(" ")
        return self.outcome.pendingTransactions


# Strategia complessa a piacere, con stop-loss e takeprofit
class ComplexStrategy(BuyAndHoldTradingStrategy):

    def __init__(self, in_port):
        super().__init__(in_port)
        self.description = "Custom"
        self.outcome.description = self.description

    def calc_suggested_transactions(self, sell_all=True, initial_buy=True, w_short=1.0, w_long=1.0):
        # Estendo la strategia base "BUY & HOLD"
        # per confrontare mele con mele, partirei sempre dal Buy and Hold
        if initial_buy:
            super().calc_suggested_transactions(sell_all=False)
        # w_short e w_long sono i moltiplicatori delle banda di Bollingher short e long
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            days_short = self.outcome.days_short
            days_long = self.outcome.days_long
            boll_multi = w_long
            days_buy = []
            quot_buy = []
            days_sell = []
            quot_sell = []
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.outcome.start_date, datetime.time.min) + datetime.timedelta(days=days_long),
                                         datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1),
                                                                   datetime.time.min)):
                # mi assicuro che esistano quotazioni per l'asset, che non sia una valuta e che la varianza sia
                # significativa, altrimenti siamo in una fase di spostamento laterale
                if asset.history.loc[dd.date(), 'Close'] > 0.0 and asset.assetType.assetType != "currency" and asset.history.loc[dd.date(), 'std_short'] > 0.03 * asset.history.loc[dd.date(), 'sma_short']:

                    prev_day = dd.date() - datetime.timedelta(days=1)
                    boll_up_old = asset.history.loc[prev_day, 'sma_long'] + boll_multi * asset.history.loc[prev_day, 'std_long']
                    boll_down_old = asset.history.loc[prev_day, 'sma_long'] - boll_multi * asset.history.loc[prev_day, 'std_long']
                    quot_old = asset.history.loc[prev_day, 'Close']
                    quot = asset.history.loc[dd.date(), 'Close']
                    boll_up = asset.history.loc[dd.date(), 'sma_long'] + boll_multi * asset.history.loc[dd.date(), 'std_long']
                    boll_down = asset.history.loc[dd.date(), 'sma_long'] - boll_multi * asset.history.loc[dd.date(), 'std_long']
                    sma_long = asset.history.loc[dd.date(), 'sma_long']
                    sma_long_old = asset.history.loc[prev_day, 'sma_long']
                    sma_short = asset.history.loc[dd.date(), 'sma_short']
                    sma_short_old = asset.history.loc[prev_day, 'sma_short']
                    boll_up2 = asset.history.loc[dd.date(), 'sma_long'] + boll_multi * 2 * asset.history.loc[dd.date(), 'std_long']
                    boll_up2_old = asset.history.loc[prev_day, 'sma_long'] + boll_multi * 2 * asset.history.loc[prev_day, 'std_long']
                    boll_down2 = asset.history.loc[dd.date(), 'sma_long'] - boll_multi * 2 * asset.history.loc[
                        dd.date(), 'std_long']
                    boll_down2_old = asset.history.loc[prev_day, 'sma_long'] - boll_multi * 2 * asset.history.loc[
                        prev_day, 'std_long']

                    if quot > boll_up and quot_old < boll_up_old:
                        # BUY
                        reason = "TRENDING UP"
                        logging.debug("\t" + reason + ": Requesting BUY for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']))
                        logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(
                            Transaction("BUY", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                  reason))
                        days_buy.append(dd.date())
                        quot_buy.append(quot)
                    elif quot < boll_down and quot_old > boll_down_old:
                        #SELL
                        reason = "TRENDING DOWN"
                        logging.debug("\t" + reason + ": Requesting SELL for " + str(key) + " on " + str(
                            dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(
                            asset.history.loc[dd.date(), 'Close']))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0, reason))
                        days_sell.append(dd.date())
                        quot_sell.append(quot)
            print(".", end="", flush=True)
            # BUY_points = pd.DataFrame({'Date': days_buy, 'Quotation': quot_buy})
            # SELL_points = pd.DataFrame({'Date': days_sell, 'Quotation': quot_sell})
            # ax = asset.history['Close'].plot(title=asset.symbol)
            # BUY_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="green", alpha=0.5)
            # SELL_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="red", alpha=0.5)
            # plt.show()
            if sell_all:
            # l'ultimo giorno vendo tutto.
             if asset.assetType.assetType != "currency":
                logging.info("\tRequesting SELL for " + str(key) + " on " + str(self.outcome.end_date))
                dailyPendTx = self.outcome.pendingTransactions[self.outcome.end_date]
                dailyPendTx.append(Transaction("SELL", asset, self.outcome.end_date, 0, 0.0, self.description))
        print(" ")
        return self.outcome.pendingTransactions

    def exec_trade(self, t : Transaction):
        # TODO: spostare order value come parametro di questo metodo, che è l'unico posto in cui viene usato
        # TODO: verificare che lo stato della Transazione sia Pending
        # recupero l'asset su cui devo operare
        logging.debug("Executing transaction: " + str(t))
        asset = self.outcome.assets[t.asset.symbol]

        #recupero il fattore di conversione per la valuta
        GBPEUR = self.outcome.assets['GBP'].history.loc[t.when]['Open'] / 100.0
        CHFEUR = self.outcome.assets['CHF'].history.loc[t.when]['Open']
        USDEUR = self.outcome.assets['USD'].history.loc[t.when]['Open']

        curr_conv = 1.0
        if asset.currency != "EUR":
            if asset.currency == "USD":
                curr_conv = USDEUR
            elif asset.currency == "GBP":
                curr_conv = GBPEUR
            elif asset.currency == "CHF":
                curr_conv = CHFEUR
        logging.debug(asset.currency + " curr_conv " + str(curr_conv))

        if t.verb == "BUY":
            logging.debug("Buying " + str(t))
            # TODO: improve Buying Quantity calculation...

            #  assumo di eseguire gli ordini di BUY e SELL come prima
            #  azione della giornata, avendoli calcolati la sera del giorno prima
            logging.debug("asset price " + str(asset.history.loc[t.when]['Open']))
            quantity = math.floor(self.BUY_ORDER_VALUE / (asset.history.loc[t.when]['Open']*curr_conv))
            asset_price = quantity * asset.history.loc[t.when]['Open'] * curr_conv
            commission = asset_price * asset.assetType.buyCommission
            if self.outcome.por_history.loc[t.when]['Liquidity'] >= (asset_price + commission) and quantity > 0.0 and asset.history.loc[t.when]['OwnedAmount'] == 0:
                # eseguo tx
                # diminuisco liquidità
                self.outcome.por_history.loc[t.when]['Liquidity'] -= (asset_price + commission)
                # aumento il monte commissioni
                self.outcome.por_history.loc[t.when]['TotalCommissions'] += commission
                # modifico average buy price
                asset.history.loc[t.when]['AverageBuyPrice'] = (asset.history.loc[t.when]['OwnedAmount']*asset.history.loc[t.when]['AverageBuyPrice'] + asset_price)/(asset.history.loc[t.when]['OwnedAmount'] + quantity)
                # aumento quantità posseduta
                asset.history.loc[t.when]['OwnedAmount'] += quantity
                t.state = "executed"
                t.quantity = quantity
                t.value = asset_price
                logging.info("Tx " + str(t) + "\tvalue: " + str(asset_price))
                self.outcome.executedTransactions.append(t)
            else:
                # tx fallita per mancanza di liquidità
                t.state = "failed"
                if asset.history.loc[t.when]['OwnedAmount'] == 0:
                    t.note += "Not enough liquidity. Transaction" + str(t) + " failed."
                    logging.debug("Tx failed, Not enough liquidity. (Avail. Liquidity: " + str(self.outcome.por_history.loc[t.when]['Liquidity']) + ")")
                else:
                    t.note += "Asset already in portfolio. Transaction" + str(t) + " failed."
                    logging.debug("Tx failed, Asset " + asset.symbol + " already in portfolio")
                self.outcome.failedTransactions.append(t)
        elif t.verb == "SELL":
            logging.debug("Selling " + str(t))
            if asset.history.loc[t.when]['OwnedAmount'] > 0.0:
                # vendo
                quantity = asset.history.loc[t.when]['OwnedAmount']
                asset_price = quantity * asset.history.loc[t.when]['Open'] * curr_conv
                commission = asset_price * asset.assetType.buyCommission
                asset.history.loc[t.when]['OwnedAmount'] = 0.0
                # calcolo le tasse
                tax = (asset_price - quantity * asset.history.loc[t.when]['AverageBuyPrice']) * asset.assetType.tax_rate
                #aggiorno liquidità
                self.outcome.por_history.loc[t.when]['Liquidity'] += (asset_price - commission - tax)
                # aumento il monte commissioni
                self.outcome.por_history.loc[t.when]['TotalCommissions'] += commission
                # aggiorno le tasse totali
                self.outcome.por_history.loc[t.when]['TotalTaxes'] += tax
                # FIXME: devo aggiornare le tasse su ciascuna azione
                t.state = "executed"
                t.quantity = quantity
                t.value = asset_price
                logging.info("Tx " + str(t) + "\tvalue: " + str(asset_price))
                self.outcome.executedTransactions.append(t)
            else:
                t.state = "failed"
                t.note += "Nothing to SELL. Transaction" + str(t) + " failed."
                logging.debug("Tx failed, Nothing to SELL")
                self.outcome.failedTransactions.append(t)
        elif t.verb == "DIVIDEND":
            logging.debug("DVND " + str(t))
            tax = asset.assetType.tax_rate * curr_conv * asset.history.loc[t.when]['OwnedAmount'] * t.value
            logging.debug("TAX: " + str(tax))
            net_divd = asset.history.loc[t.when]['OwnedAmount'] * t.value * curr_conv * (1 - asset.assetType.tax_rate)
            logging.debug("Net dividend: " + str(net_divd))
            self.outcome.por_history.loc[t.when]['Liquidity'] += net_divd
            t.state = "executed"
            # aggiorno le tasse totali
            self.outcome.por_history.loc[t.when]['TotalTaxes'] += tax
            t.quantity = asset.history.loc[t.when]['OwnedAmount']
            self.outcome.por_history.loc[t.when]['TotalDividens'] += net_divd
            self.outcome.executedTransactions.append(t)
            logging.debug("Dividend from " + str(asset.symbol) + " tot Value: " + str(asset.history.loc[t.when]['OwnedAmount'] * t.value * curr_conv * (1 - asset.assetType.tax_rate)))
        else:
            logging.debug("Ignoring Tx: " + str(t))
            t.state = "failed"
            t.note += " - no instructions for VERB: " + t.verb
            self.outcome.failedTransactions.append(t)
        # TODO: rimuovere transazione da pendingTransactions
