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


# Per definire una strategia più complessa estendo la classe BuyAndHoldTradingStrategy e faccio overload del metodo
# che calcola le suggested transactions
# la parte difficile è capire quando portare
# Buy signal => SOTTO BOLLINGHER, In crescita di più del 10% in 2 settimane
# SELL = > STOP LOSS, SOPRA BOLLINGHER
# in tutti i casi, nessun asset può occupare più del 10% del mio portafoglio
class CustomStrategy(sim_trade.BuyAndHoldTradingStrategy):

    def __init__(self, in_port):
        super().__init__(in_port)
        self.description = "CustomStrategy"
        self.BUY_ORDER_VALUE = 5000.0
        self.outcome.description = self.description

    def calc_suggested_transactions(self):
        # Strategia base "BUY & HOLD"
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, sim_trade.Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            stop_loss = 0.0
            stop_loss_pct = 0.8
            #take_profit = 9999999.0
            #take_profit_pct = 1.2
            #days_short = 20
            days_long = 40
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
                    # set new stop_loss
                    # TODO: forse STOP-LOSS e TAKE-PROFIT sarebbe meglio calcolarli durante in trading vero e proprio...
                    if asset.history.loc[dd.date(), 'Close'] < stop_loss:
                        logging.debug("\tSTOP LOSS: Requesting SELL for " + str(key) + " on " + str(dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']))
                        #logging.debug("assetType: " + str(asset.assetType))
                        dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                        dailyPendTx.append(sim_trade.Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0, "STOP LOSS"))
                        stop_loss = 0.0
                        #take_profit = 9999999.0
                    else:
                        prev_day = dd.date() - datetime.timedelta(days=1)
                        boll_up_old = asset.history.loc[prev_day, 'sma_short'] + 2* asset.history.loc[prev_day, 'std_short']
                        boll_down_old = asset.history.loc[prev_day, 'sma_short'] - 2* asset.history.loc[prev_day, 'std_short']
                        quot_old = asset.history.loc[prev_day, 'Close']
                        quot = asset.history.loc[dd.date(), 'Close']
                        boll_up = asset.history.loc[dd.date(), 'sma_short'] + 2* asset.history.loc[dd.date(), 'std_short']
                        boll_down = asset.history.loc[dd.date(), 'sma_short'] - 2* asset.history.loc[dd.date(), 'std_short']

                        if quot > boll_down and quot_old < boll_down_old:
                            # BUY
                            reason = "BOLLINGER"
                            # stop_loss = asset.history.loc[dd.date(), 'Close'] * stop_loss_pct
                            # take_profit = asset.history.loc[dd.date(), 'Close'] * take_profit_pct
                            logging.debug("\t" + reason + ": Requesting BUY for " + str(key) + " on " + str(
                                dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(asset.history.loc[dd.date(), 'Close']) + "\tSetting stop_loss: " + str(stop_loss))
                            logging.debug("assetType: " + str(asset.assetType))
                            dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                            dailyPendTx.append(
                                sim_trade.Transaction("BUY", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                      reason))
                            days_buy.append(dd.date())
                            quot_buy.append(quot)
                        elif quot < boll_up and quot_old > boll_up_old:
                            #SELL
                            reason = "BOLLINGER"
                            logging.debug("\tBOL: Requesting SELL for " + str(key) + " on " + str(
                                dd.date() + datetime.timedelta(days=1)) + "\tquotation: " + str(
                                asset.history.loc[dd.date(), 'Close']))
                            dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                            dailyPendTx.append(
                                sim_trade.Transaction("SELL", asset, dd.date() + datetime.timedelta(days=1), 0, 0.0,
                                                      reason))
                            stop_loss = 0.0
                            days_sell.append(dd.date())
                            quot_sell.append(quot)
            print(".", end="", flush=True)
            # BUY_points = pd.DataFrame({'Date': days_buy, 'Quotation': quot_buy})
            # SELL_points = pd.DataFrame({'Date': days_sell, 'Quotation': quot_sell})
            # ax = asset.history['Close'].plot(title=asset.symbol)
            # BUY_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="green", alpha=0.5)
            # SELL_points.plot(kind='scatter', ax=ax, x='Date', y='Quotation', color="red", alpha=0.5)
            # plt.show()
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
        myPortfolio.calc_stats()
        myPortfolio.fill_history_gaps()
        # mi salvo il calcolo per velocizzare i miei tests
        file_handle = open("./data/save.port.data", "wb")
        logging.info("\nSaving Initial Portfolio and quotations to: " + str(file_handle.name))
        pickle.dump(myPortfolio, file_handle)
        file_handle.close()
    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    my_trading_strategy = CustomStrategy(myPortfolio)
    #my_trading_strategy = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
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
    # esamino un'azione per capire cosa ho individuato come punti d'inversione
    final_port.assets['AMP.MI'].history['Close'].plot()
    # A scopo didattico, provo a visualizzare i punti di BUY e SELL calcolati
    # costruire un dataframe con i segnali di BUY per AMP.MI
    # pandas_sma_short = final_port.assets['AMP.MI'].history['Close'].history.rolling(window=30).mean()
    # pandas_sma_short.plot()
    # AX = AX
    # plt.scatter()
    # plt.show()