# ver 1.0
import pandas as pd
# nota bene, ho patchato l'ultima versione di pandas_datareader per fissare un errore su yahoo split
from pandas_datareader import data as pdr
import requests_cache
import datetime
import logging
import sys
import copy as cp
import arrow as ar


# Defining Basic Classes

# I need a container to track all the characteristics of a specific asset class, e.g. different commissions, dividends.
class AssetClass:
    def __init__(self, asset_type: str, buy_commission: float, annual_fee: float):
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


# I create the asset classes I want in my Portfolio for now
EQUITY = AssetClass("equity", 0.005, 0)
ETC = AssetClass("ETC", 0.005, 0)
CURRENCY = AssetClass("currency", 0.001, 0)


# I define the concept of Asset
class Asset:
    def __init__(self, assetType: AssetClass, name: str, symbol: str, market: str, currency: str, quantity: float = 0.0,
                 avg_buy_price: float = 0,
                 avg_buy_curr_chg: float = 0,
                 history: pd.DataFrame = pd.DataFrame(), amount=0.0):
        self.assetType = assetType
        self.name = name
        self.symbol = symbol
        self.market = market
        self.currency = currency
        # quantity, amount, average_buy_price, avg_buy_curr_chg variano nel tempo, aggiungo delle colonne ai DataFrame
        # delle quotazioni
        #self.quantity = quantity  # per asset discreti (e.g. azioni)
        #self.amount = amount  # per le valute
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
        if self.verb == "DIVIDEND" or self.verb == "SPLIT":
            return (str(self.when) + " : " + self.verb + " " + self.asset.symbol + " " + str(self.value)) + " " + str(
                self.quantity)
        else:
            return str(self.when) + " : " + self.verb + " " + str(self.quantity) + " " + self.asset.symbol

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
    def __init__(self, start_date, end_date, initial_capital, description="Default Portfolio", total_commissions=0.0):
        self.assets = dict()
        # elenco di asset acceduti via simbolo. un giorno capirò se abbia senso una struttura dati diversa
        self.defCurrency = "EUR"
        self.pendingTransactions = []
        self.executedTransactions = []
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.description = description
        self.total_commissions = total_commissions

    def loadAssetList(self):
        # Considero titoli in 4 valute ma normalizzo tutto su EUR
        # in future evoluzioni valuerò se rendere la valuta interna parametrica
        #self.assets["EUR"] = Asset(CURRENCY, "EUR", "EUREUR=X", "FX", "EUR")
        self.assets["USD"] = Asset(CURRENCY, "USD", "USDEUR=X", "FX", "USD")
        self.assets["GBP"] = Asset(CURRENCY, "GBP", "GBPEUR=X", "FX", "GBP")
        self.assets["CHF"] = Asset(CURRENCY, "CHF", "CHFEUR=X", "FX", "CHF")
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

        # Titolo CH da me selezionati
        self.assets["ALC.SW"] = Asset(EQUITY, "ALCON N", "ALC.SW", "VIRTX", "CHF")
        self.assets["NOVN.SW"] = Asset(EQUITY, "NOVARTIS N", "NOVN.SW", "VIRTX", "CHF")
        self.assets["SOON.SW"] = Asset(EQUITY, "SONOVA HLDG N", "SOON.SW", "VIRTX", "CHF")
        self.assets["NESN.SW"] = Asset(EQUITY, "Nestle S.A.", "NESN.SW", "VIRTX", "CHF")
        self.assets["SREN.SW"] = Asset(EQUITY, "Swiss Re AG", "SREN.SW", "VIRTX", "CHF")
        self.assets["ROG.SW"] = Asset(EQUITY, "Roche Holding AG", "ROG.SW", "VIRTX", "CHF")

        # Titoli GBP da me selezionati
        self.assets["BA.L"] = Asset(EQUITY, "BAE SYSTEMS", "BA.L", "LSE", "GBP")
        self.assets["BP.L"] = Asset(EQUITY, "BP", "BP.L", "LSE", "GBP")
        self.assets["BT-A.L"] = Asset(EQUITY, "BT GROUP", "BT-A.L", "LSE", "GBP")
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

        # Titoli EUR da me selezionati
        self.assets["AMP.MI"] = Asset(EQUITY, "Amplifon", "AMP.MI", "MTA", "EUR")
        self.assets["BRE.MI"] = Asset(EQUITY, "BREMBO", "BRE.MI", "MTA", "EUR")
        self.assets["CPR.MI"] = Asset(EQUITY, "CAMPARI", "CPR.MI", "MTA", "EUR")
        self.assets["CERV.MI"] = Asset(EQUITY, "CERVED GROUP", "CERV.MI", "MTA", "EUR")
        self.assets["DSY.PA"] = Asset(EQUITY, "Dassault Systèmes SE", "DSY.PA", "EQUIDUCT", "EUR")
        self.assets["DIA.MI"] = Asset(EQUITY, "DIASORIN", "DIA.MI", "MTA", "EUR")
        self.assets["ENEL.MI"] = Asset(EQUITY, "ENEL", "ENEL.MI", "MTA", "EUR")
        self.assets["ENI.MI"] = Asset(EQUITY, "ENI", "ENI.MI", "MTA", "EUR")
        self.assets["FCA.MI"] = Asset(EQUITY, "FCA", "FCA.MI", "MTA", "EUR")
        self.assets["GEO.MI"] = Asset(EQUITY, "GEO", "GEO.MI", "MTA", "EUR")
        self.assets["KER.PA"] = Asset(EQUITY, "Kering SA", "KER.PA", "EQUIDUCT", "EUR")
        self.assets["MONC.MI"] = Asset(EQUITY, "MONCLER", "MONC.MI", "MTA", "EUR")
        self.assets["UCG.MI"] = Asset(EQUITY, "UNICREDIT", "UCG.MI", "MTA", "EUR")
        self.assets["EL.PA"] = Asset(EQUITY, "EssilorLuxottica Societe anonyme", "EL.PA", "EQUIDUCT", "EUR")
        self.assets["FME.DE"] = Asset(EQUITY, "FRESENIUS MEDICAL", "FME.DE", "EQUIDUCT", "EUR")
        self.assets["VNA.DE"] = Asset(EQUITY, "VONOVIA", "VNA.DE", "XETRA", "EUR")
        self.assets["MC.PA"] = Asset(EQUITY, "LVMH Moët Hennessy Louis Vuitton S.E.", "MC.PA", "EQUIDUCT", "EUR")
        self.assets["VVD.F"] = Asset(EQUITY, "Veolia Environnement S.A.", "VVD.F", "EQUIDUCT", "EUR")

    def fill_history_gaps(self):
        logging.debug("Entering fill_history_gaps")
        for key, asset in sorted(self.assets.items()):
            # create a set containing all dates in Range
            logging.debug("Processing :" + asset.symbol)
            if asset.symbol == self.defCurrency:
                asset.history = pd.DataFrame() # devo definire la struttura
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.start_date, datetime.time.min),
                                     datetime.datetime.combine(self.end_date, datetime.time.min)):
                print("Asset: "+ asset.symbol + "\tdate: " + str(dd.date()))
                try:
                    last_row = asset.history.loc[str(dd.date()), : ]
                except KeyError as e:
                    # non esiste l'indice
                    logging.debug("Missing Index: " + str(dd.date()) + " in Asset " + str(asset.symbol))
                    t = datetime.datetime.combine(dd.date(), datetime.time.min)
                    asset.history.loc[t] = last_row
                    #devo sistemare, last_row, potrebbe non esistere se manca la prima data.
                except Exception as e:
                    logging.exception("Unexpected error:" + str(e))
                    exit(-1)
            # asset.history = asset.history.sort_index()
            # estendo il DataFrame aggiungendo la colonna OwnedAmount
            asset.history['OwnedAmount'] = 0.0


    def loadQuotations(self):
        # get Quotations & Dividends for all Assets in myPortfolio
        for key, value in sorted(self.assets.items()):
            assert isinstance(value, Asset)
            logging.info("Now retrieving quotations for:\t" + str(key) + "\t" + str(value))
            if str(key) != str(value.symbol):
                logging.warning("warning: " + str(key) + " NOT equal to " + str(value.symbol))
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento recupero
            # le quotazioni storiche
            if str(key) != self.defCurrency:
                value.history = pdr.DataReader(value.symbol, "yahoo", self.start_date, self.end_date,
                                                           session=session)
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
                            self.pendingTransactions.append(
                                Transaction(row["action"], value, index, 0, row["value"]))
                    except Exception as e:
                        logging.error("Failed to get dividends for " + str(value.name) + "(" + str(key) + ")")
                        logging.exception("Unexpected error:" + str(e))


# Creo la Classe TradingStrategy
# analizza il portafoglio un asset alla volta.
# Se voglio imporre vincoli tra asset, lo faccio all'interno della Simulazione
# ad esempio ETC oro deve essere tra 5% e 10% del valore totale del Portafoglio
# Devo avere valuta per investire, etc...
# come strategia di Trading Baseline, implemento BUY&HOLD
# se voglio fare strategie più sofisticate eredito e faccio override del metodo 'suggested_transactions'
class BuyAndHoldTradingStrategy:
    def __init__(self, in_port: Portfolio):
        self.description = "BUY and HOLD"
        # clono il Portafoglio in Input così lo posso modificare
        self.outcome = cp.deepcopy(in_port)
        # setto un valore standard per i BUY oders, in modo che sia possibile investire su tutti gli asset
        self.BUY_ORDER_VALUE = self.outcome.initial_capital / len(self.outcome.assets.keys())
        logging.debug("Setting BUY order value to: " + str(self.BUY_ORDER_VALUE))
        # voglio ricevere un portafoglio iniziale che contenga tutti gli input per eseguire la simulazione
        # voglio ricevere una TradingStrategy che contenga le regole da applicare
        # restiruisco un nuovo Portafoglio elaborato con le regole

    def calc_suggested_transactions(self):
        # Strategia base "BUY & HOLD"
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            print(asset.history)
            if asset.history.loc[str(self.outcome.start_date), 'OwnedAmount'] == 0 and str(key) != self.outcome.defCurrency:
                logging.info("\tRequesting BUY for " + str(key) + " on " + str(self.outcome.start_date +
                                                                               datetime.timedelta(days=1)))
                self.outcome.pendingTransactions.append(Transaction("BUY", asset, self.outcome.start_date +
                                                               datetime.timedelta(days=1), 0, 0.0, self.description))
        return self.outcome

    # Creo il metodo TradingSimulation che deve iterare dentro un range di date, eseguire gli ordini e aggiornare i valori
    def runTradingSimulation(self):
        logging.debug("Processing portfolio \'{0}\' start_date = {1} end_date = {2}".format(self.outcome.description,
                                                                                            str(self.outcome.start_date),
                                                                                            str(self.outcome.end_date)))
        # sorting Pending Transactions:
        self.outcome.pendingTransactions.sort(reverse=False, key=Transaction.to_datetime)
        for r in ar.Arrow.range('day', datetime.datetime.combine(self.outcome.start_date, datetime.time.min),
                                datetime.datetime.combine(self.outcome.end_date, datetime.time.min)):
            logging.debug("\tProcessing Trading Day " + str(r.date()))
            # dovrei iterare sui giorni ed eseguire le transazioni
            #
        return self.outcome


if __name__ == "__main__":
    # cominciamo a lavorare
    # setting up Logging
    logging.basicConfig(filename='./logs/backtrace.log', level=logging.DEBUG)
    logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info("******************************************************")
    logging.info("*      NEW START : " + str(datetime.datetime.now()) + "        *")
    logging.info("******************************************************")
    # setto una cache per i pandas_datareader
    expire_after = datetime.timedelta(days=3)
    session = requests_cache.CachedSession(cache_name='./data/cache', backend='sqlite', expire_after=expire_after)

    # print DataFrame wide
    pd.set_option('display.width', 1000)

    # Last day
    end_date = datetime.date.today()
    # First day
    start_date = end_date - datetime.timedelta(days=365 * 1)
    initial_capital = 100000  # EUR

    # Create and Initialise myPortfolio
    myPortfolio = Portfolio(start_date, end_date, initial_capital)
    myPortfolio.loadAssetList()
    timestamp = datetime.datetime.now()
    logging.info("\nRetrieving assets history from: " + str(start_date) + " to: " + str(end_date))
    myPortfolio.loadQuotations()
    logging.info("Retrieve completed in " + str(datetime.datetime.now() - timestamp))
    # adesso dovrei aver recuperato tutti i dati...
    # Devo sistemare i gap nelle date. Non posso farlo prima perché la natura multiThread delle librerie crea dei casini
    myPortfolio.fill_history_gaps()
    # possiamo cominciare a pensare a cosa fare...

    # devo definire una strategia di Trading
    my_trading_strategy = BuyAndHoldTradingStrategy(myPortfolio)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_outcome = my_trading_strategy.calc_suggested_transactions()
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))

    # processo tutte le transazioni pending e vedo cosa succede
    timestamp = datetime.datetime.now()
    logging.info("\nExecuting trades")
    my_trading_strategy.runTradingSimulation()
    logging.info("Trades completed in " + str(datetime.datetime.now() - timestamp))

    # elaborazione finita proviamo a visualizzare qualcosa
    print()
    exit(0)
    # test sort
    my_strategy_outcome.pendingTransactions.append(Transaction("SPLIT", my_strategy_outcome.assets["AMP.MI"],
                                                               datetime.date(2019, 5, 16)))
    my_strategy_outcome.pendingTransactions.append(Transaction("SELL", my_strategy_outcome.assets["AMP.MI"],
                                                               datetime.date(2019, 5, 16)))
    my_strategy_outcome.pendingTransactions.sort(key=Transaction.to_datetime)
    for t in my_strategy_outcome.pendingTransactions:
        print(t)
    print("fin qui tutto OK :)")

##########################
# TODOs
# devo scrivere i metodi per processare le transazioni:
# SPLIT -> lo ignoro
# DIVIDEND -> eseguo la transazione sul conto valuta corrispondente calcolando l'importo da accreditare
# SELL -> accredito su conto valuta; in teoria il segnale è già sul giorno successivo, (potrebbe non esistere quotazione
# per quel giorno)
# BUY -> converto tutti i conti valuta in EURO e provo (il max order è in euro)
# devo scrivere un metodo per calcolare il valore del portafoglio mano a mano che passa il tempo.... Da capire
# la quantità/amount di un asset varia nel tempo, per cui sarebbe opportuno aggiungere una colonna al DataFrame delle
# quotazioni inoltre sarebbe opportuno riempire i gap di data nell'indice trascinando i valori del giorno precedente,
# ma è da farsi dopo aver calcolato i segnali.
# Finally... Non mi resta che implementare la varie strategie e graficare con matplotlib
