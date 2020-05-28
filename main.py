# ver 1.0
import datetime
import logging
import os
import pandas as pd
import sim_trade
import arrow as ar
import matplotlib.pyplot as plt
import pickle
import math


class RollingStatistic(object):
    # https://jonisalonen.com/2014/efficient-and-accurate-rolling-standard-deviation/

    def __init__(self, window_size, average, variance):
        self.N = window_size
        self.average = average
        self.variance = variance
        self.stddev = math.sqrt(variance)

    def update(self, new, old):
        oldavg = self.average
        newavg = oldavg + (new - old)/self.N
        self.average = newavg
        # FIXME: secondo me è sbagliato il calcolo della varianza
        self.variance += (new-old)*(new-newavg+old-oldavg)/(self.N-1)
        if self.variance < 0:
            self.variance = -1*self.variance
        try:
            self.stddev = math.sqrt(self.variance)
        except Exception as e:
            logging.exception(e)
            logging.debug("self.variance = " + str(self.variance))
            exit(-1)

# Per definire una strategia più complessa estendo la classe BuyAndHoldTradingStrategy e faccio overload del metodo
# che calcola le suggested transactions
# la parte difficile è capire quando portare
# Buy signal => SOTTO BOLLINGHER, In crescita di più del 10% in 2 settimane
# SELL = > STOP LOSS, SOPRA BOLLINGHER
# in tutti i casi, nessun asset può occupare più del 10% del mio portafoglio
class CustomStrategy(sim_trade.BuyAndHoldTradingStrategy):

    def calc_suggested_transactions(self):
        # Strategia base "BUY & HOLD"
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, sim_trade.Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            stop_loss = 0.0
            sma_short = 0.0
            sma_long = 0.0
            std_long = 0.0
            std_short= 0.0
            days_short = 30
            days_long = 60
            RollingStatShort = RollingStatistic(days_short, 0, 0)
            RollingStatLong = RollingStatistic(days_long, 0, 0)
            value_to_drop_short = 0.0
            value_to_drop_long = 0.0
            for dd in ar.Arrow.range('day', datetime.datetime.combine(self.outcome.start_date, datetime.time.min),
                                         datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1),
                                                                   datetime.time.min)):
                # mi assicuro che esistano quotazioni per l'asset e che non sia una valuta
                if asset.history.loc[dd.date(), 'Close'] > 0.0 and asset.assetType.assetType != "currency":
                    # set new stop_loss
                    if asset.history.loc[dd.date(), 'Close'] * 0.9 > stop_loss > 0.0:
                        stop_loss = asset.history.loc[dd.date(), 'Close'] * 0.9
                    if asset.history.loc[dd.date(), 'Close'] < stop_loss:
                        logging.debug("\tSTOP LOSS: Requesting SELL for " + str(key) + " on " + str(dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']))
                        #logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(sim_trade.Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0, "STOP LOSS"))
                        stop_loss = 0.0
                    else:
                        if dd.date() >= self.outcome.start_date + datetime.timedelta(days=days_short):
                            value_to_drop_short = asset.history.loc[dd.date() - datetime.timedelta(days=days_short), 'Close']
                            if dd.date() >= self.outcome.start_date + datetime.timedelta(days=days_long):
                                value_to_drop_long = asset.history.loc[
                                    dd.date() - datetime.timedelta(days=days_long), 'Close']
                        RollingStatShort.update(asset.history.loc[dd.date(), 'Close'], value_to_drop_short)
                        RollingStatLong.update(asset.history.loc[dd.date(), 'Close'], value_to_drop_long)
                        sma_short_old = sma_short
                        sma_long_old = sma_long
                        sma_short = RollingStatShort.average
                        sma_long = RollingStatLong.average
                        std_long = RollingStatLong.stddev
                        std_short = RollingStatShort.stddev
                        #if sma_short > sma_long*1.01 or asset.history.loc[dd.date(), 'Close'] < sma_long - 2*std_long:
                        if sma_short > sma_long and sma_short_old < sma_long_old:
                        #if asset.history.loc[dd.date(), 'Close'] < (sma_long - 2*std_long):
                            # BUY
                            if sma_short > sma_long:
                                reason = "SMA"
                            else:
                                reason = "BOLLINGHER"
                            if stop_loss < asset.history.loc[dd.date(), 'Close'] * 0.9:
                                stop_loss = asset.history.loc[dd.date(), 'Close'] * 0.9
                            logging.debug("\t" + reason + ": Requesting BUY for " + str(key) + " on " + str(
                                dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']) + "Setting stop_loss: " + str(stop_loss))
                            logging.debug("assetType: " + str(asset.assetType))
                            dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                            dailyPendTx.append(
                                sim_trade.Transaction("BUY", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                      "UP TREND or LOW Value"))
            print(".", end="", flush=True)
            # l'ultimo giorno vendo tutto.
            if asset.assetType.assetType != "currency":
                logging.info("\tRequesting SELL for " + str(key) + " on " + str(self.outcome.end_date))
                dailyPendTx = self.outcome.pendingTransactions[self.outcome.end_date]
                dailyPendTx.append(sim_trade.Transaction("SELL", asset, self.outcome.end_date, 0, 0.0, self.description))
        print(" ")
        return self.outcome.pendingTransactions


if __name__ == "__main__":
    # cominciamo a lavorare
    print("\nStarting...")
    # setting up Logging
    os.remove("./logs/backtrace.log")
    logging.basicConfig(filename='./logs/backtrace.log', level=logging.DEBUG)
    #logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info("******************************************************")
    logging.info("*      NEW START : " + str(datetime.datetime.now()) + "        *")
    logging.info("******************************************************")


    # print DataFrame wide
    pd.set_option('display.width', 1000)

    # Last day
    #end_date = datetime.date.today()
    end_date = datetime.date(2020, 5, 25)
    # First day
    start_date = end_date - datetime.timedelta(days=365*5)
    initial_capital = 300000.0  # EUR


    try:
        # se esiste questo file, lo carico e risparmio qualche minuto
        file_handle = open("./data/save.port.data", "rb")
        print("Loading previously saved Initial Portfolio and quotations")
        logging.info("\nLoading previously saved Initial Portfolio and quotations from: " + str(file_handle.name))
        myPortfolio = pickle.load(file_handle)
        file_handle.close()
    except FileNotFoundError:
        # Create and Initialise myPortfolio
        myPortfolio = sim_trade.Portfolio(start_date, end_date, initial_capital)
        print("\tInit Portfolio")
        myPortfolio.loadAssetList()
        timestamp = datetime.datetime.now()
        logging.info("\nRetrieving assets history from: " + str(start_date) + " to: " + str(end_date))
        print("\tLoading quotations")
        myPortfolio.loadQuotations('./data/cache')
        logging.info("Retrieve completed in " + str(datetime.datetime.now() - timestamp))
        # adesso dovrei aver recuperato tutti i dati...
        # Devo sistemare i gap nelle date perché non voglio continuare a controllare se un indice esiste o meno...
        print("\tFixing Data")
        myPortfolio.fill_history_gaps()
        # mi salvo il calcolo per velocizzare i miei tests
        logging.info("\nSaving Initial Portfolio and quotations to: " + str(file_handle.name))
        file_handle = open("./data/save.port.data", "wb")
        pickle.dump(myPortfolio, file_handle)
        file_handle.close()
    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    my_trading_strategy = CustomStrategy(myPortfolio)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_outcome = my_trading_strategy.calc_suggested_transactions()
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))

    # processo tutte le transazioni pending e vedo cosa succede
    timestamp = datetime.datetime.now()
    logging.info("\nExecuting trades")
    print("\tSimulating trading")
    final_port = my_trading_strategy.runTradingSimulation()
    logging.info("Trades completed in " + str(datetime.datetime.now() - timestamp))

    # elaborazione finita visualizziamo l'outcome
    print("\nEnded, please check log file.\n")
    print("Simulation Outcome:")
    print("\nInitial Portfolio")
    myPortfolio.printReport()
    print("\nFinal Portfolio:")
    final_port.printReport()
    print("\nNota bene, se il NetValue finale e' inferiore a initial_capital + Dividendi, di fatto c'e' stata una perdita sul capitale")
    print("Se nell'ultimo giorno, il totale delle tasse si abbassa, di fatto si sta scontando un Tax Credit Futuro\n")
    print(final_port.por_history.loc[end_date - datetime.timedelta(days=1)])
    print("\nExecuted Tx: ")
    for t in final_port.executedTransactions:
        print(" Tx: " + str(t))
    print(final_port.por_history)
    #final_port.por_history.plot(kind='line', y='NetValue')
    final_port.por_history['NetValue'].plot(kind='line')
    plt.show()