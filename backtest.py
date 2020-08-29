# ver 1.0
import datetime
import logging
import os
import pandas as pd
import sim_trade
import matplotlib.pyplot as plt
import pickle
from sim_trade import BuyAndHoldTradingStrategy
from sim_trade import InvBollbandsStrategy
from sim_trade import BollbandsStrategy

if __name__ == "__main__":
    # cominciamo a lavorare
    print("\nStarting...")
    # setting up Logging
    log_file_name = "./logs/backtesting.log"
    try:
        os.remove(log_file_name)
    except Exception as e:
        print(e)
    logging.basicConfig(filename=log_file_name, level=logging.DEBUG)
    # logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info("******************************************************")
    logging.info("*      NEW START : " + str(datetime.datetime.now()) + "        *")
    logging.info("******************************************************")

    # print DataFrame wide
    pd.set_option('display.width', 1000)

    # Last day
    end_date = datetime.date.today()
    # end_date = datetime.date(2020, 8, 7)
    # First day
    # start_date = datetime.date(2015, 6, 9)
    start_date = datetime.date(2017, 9, 5)
    initial_capital = 1000000.0  # 1.000.000 EUR
    # se initial capital è 1.000.000, metto l'ordine a 50.000 per avere dei vincoli, oppure 5.000 per essere
    # virtualmente senza vincoli di liquidità
    max_order = 34400.0

    filename = "./data/saved.mkts.data." + str(start_date) + '-' + str(end_date)
    try:
        # se esiste questo file, lo carico e risparmio qualche minuto
        file_handle = open(filename, "rb")
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
        print("\tCalculating Basic Stats")
        myPortfolio.calc_stats(days_short=20, days_long=150)
        print("\tFixing Data")
        myPortfolio.fill_history_gaps()
        # mi salvo il calcolo per velocizzare i miei tests
        file_handle = open(filename, "wb")
        logging.info("\nSaving Initial Portfolio and quotations to: " + str(file_handle.name))
        pickle.dump(myPortfolio, file_handle)
        file_handle.close()
    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    # my_trading_strategy = BuyAndHoldTradingStrategy(myPortfolio)
    my_trading_strategy = InvBollbandsStrategy(myPortfolio)
    # my_trading_strategy = BollbandsStrategy(myPortfolio)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_outcome = my_trading_strategy.calc_suggested_transactions(w_short=1.0, w_long=1.0)
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))

    # processo tutte le transazioni pending e vedo cosa succede
    timestamp = datetime.datetime.now()
    logging.info("\nExecuting trades")
    print("\tSimulating trading")
    final_port = my_trading_strategy.runTradingSimulation(orderValue=max_order)
    logging.info("Trades completed in " + str(datetime.datetime.now() - timestamp))

    # calculating base case
    if True:
        print("\nCalculating base case")
        base_strat = BuyAndHoldTradingStrategy(myPortfolio)
        base_outcome = base_strat.calc_suggested_transactions()
        base_port = base_strat.runTradingSimulation(orderValue=max_order)
        base_port.por_history['NetValue'].plot(kind='line')
        # TODO: bisognerebbe salvarlo serializzato come fatto per il portafolgio iniziale

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
    # grandezze medie e minime
    print("\nAverages:")
    print(final_port.por_history.mean())
    print("\nMins:")
    print(final_port.por_history.min())
    print("\nExecuted Tx: ")
    for t in final_port.executedTransactions:
        print(" Tx: " + str(t))

    # print(final_port.por_history)
    # final_port.por_history.plot(kind='line', y='NetValue')
    final_port.por_history['NetValue'].plot(kind='line')
    # myPortfolio.por_history['NetValue'].plot(kind='line')
    plt.show()
    # esamino un'azione per capire cosa ho individuato come punti d'inversione
    # final_port.assets['AMP.MI'].history['Close'].plot()
    # A scopo didattico, provo a visualizzare i punti di BUY e SELL calcolati
    # costruire un dataframe con i segnali di BUY per AMP.MI
    # pandas_sma_short = final_port.assets['AMP.MI'].history['Close'].history.rolling(window=30).mean()
    # pandas_sma_short.plot()
    # AX = AX
    # plt.scatter()
    # plt.show()
