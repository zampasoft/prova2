# ver 1.0
import datetime
import logging
import os
import pandas as pd
import sim_trade
import arrow as ar
import matplotlib.pyplot as plt

# Per definire una strategia più complessa estendo la classe BuyAndHoldTradingStrategy e faccio overload del metodo
# che calcola le suggested transactions
class CustomStrategy(sim_trade.BuyAndHoldTradingStrategy):

    def calc_suggested_transactions(self):
        # Strategia base "BUY & HOLD"
        for key, asset in sorted(self.outcome.assets.items()):
            assert isinstance(asset, sim_trade.Asset)
            # per tutti gli asset, tranne il portafoglio stesso e la valuta di riferimento genero dei segnali di BUY o
            # SELL. Nella strategia BUY & HOLD, se il valore di un asset è 0 allora genero un BUY
            for dd in ar.Arrow.range('week', datetime.datetime.combine(self.outcome.start_date, datetime.time.min),
                                         datetime.datetime.combine(self.outcome.end_date - datetime.timedelta(days=1),
                                                                   datetime.time.min)):

                if asset.history.loc[dd.date(), 'OwnedAmount'] == 0.0 and asset.history.loc[dd.date(), 'Close'] > 0.0 \
                        and asset.assetType.assetType != "currency":
                    logging.debug("\tRequesting BUY for " + str(key) + " on " + str(dd.date() +
                                                                               datetime.timedelta(days=1)))
                    logging.debug("assetType: " + str(asset.assetType))
                    dailyPendTx = self.outcome.pendingTransactions[dd.date() + datetime.timedelta(days=1)]
                    dailyPendTx.append(sim_trade.Transaction("BUY", asset, dd.date() +
                                                               datetime.timedelta(days=1), 0, 0.0, self.description))
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
    logging.basicConfig(filename='./logs/backtrace.log', level=logging.INFO)
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