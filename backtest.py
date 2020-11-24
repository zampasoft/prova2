# ver 1.0
import datetime
import logging
import os
import pandas as pd
import sim_trade
import matplotlib.pyplot as plt
import pickle
from pandas.tseries.offsets import BDay


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
    end_date = datetime.date.today() + BDay(0)
    # end_date = datetime.date(2020, 4, 3)
    # First day
    # start_date = datetime.date(2015, 6, 9)
    start_date = datetime.date(2020, 2, 5)
    initial_capital = 1000000.0  # 1.000.000 EUR
    sell_all = False


    filename = "./data/saved.mkts.data." + str(start_date) + '-' + str(end_date.date())
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
        myPortfolio.fix_history_data()
        # mi salvo il calcolo per velocizzare i miei tests
        file_handle = open(filename, "wb")
        logging.info("\nSaving Initial Portfolio and quotations to: " + str(file_handle.name))
        pickle.dump(myPortfolio, file_handle)
        file_handle.close()
    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    # my_trading_strategy = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
    # my_trading_strategy = sim_trade.InvBollbandsStrategy(myPortfolio)
    my_trading_strategy = sim_trade.ComplexStrategy(myPortfolio)
    # my_trading_strategy = sim_trade.BollbandsStrategy(myPortfolio)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_signals = my_trading_strategy.calc_suggested_transactions(sell_all=sell_all, initial_buy=True, w_short=3.0, w_long=1.0)
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))
    # Printing raw Signals
    print("Calculation Outcome:")
    print("\nSignalled Tx: ")


    for dd in pd.date_range(start=start_date, end=end_date, freq='B'):
        for t in my_strategy_signals[dd]:
            if t.verb == "BUY" or t.verb == "SELL":
                print(" Tx: " + str(t))

    # processo tutte le transazioni pending e vedo cosa succede
    timestamp = datetime.datetime.now()
    logging.info("\nExecuting trades")
    print("\tSimulating trading")
    final_port = my_trading_strategy.runTradingSimulation(max_orders=25)
    logging.info("Trades completed in " + str(datetime.datetime.now() - timestamp))

    # calculating base case
    benchmark = myPortfolio
    if True:
        print("\nCalculating Buy & Hold")
        # base_strat = sim_trade.InvBollbandsStrategy(myPortfolio)
        # base_strat = sim_trade.BollbandsStrategy(myPortfolio)
        base_strat = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
        base_signals = base_strat.calc_suggested_transactions(sell_all=sell_all, initial_buy=True)
        base_port = base_strat.runTradingSimulation(max_orders=25)
        base_port.por_history['NetValue'].plot(kind='line', label="Buy&Hold", legend=True)
        benchmark = base_port
        print("\nCalculating InvBollingherBands")
        bounded_strat = sim_trade.InvBollbandsStrategy(myPortfolio)
        ## bounded_strat = sim_trade.BollbandsStrategy(myPortfolio)
        bounded_signals = bounded_strat.calc_suggested_transactions(sell_all=sell_all, initial_buy=True)
        bounded_port = bounded_strat.runTradingSimulation(max_orders=30)
        bounded_port.por_history['NetValue'].plot(kind='line', label="InvBollingherBands", legend=True)
        print("\nExecuted Tx: ")
        for t in bounded_port.executedTransactions:
            if t.verb == "BUY" or t.verb == "SELL":
                print(" Tx: " + str(t))
        # TODO: bisognerebbe salvarlo serializzato come fatto per il portafolgio iniziale

    # elaborazione finita visualizziamo l'outcome
    print("\nEnded, please check log file.\n")
    print("Simulation Outcome:")
    print("\nBenchmark Strategy")
    benchmark.printReport()
    print("\nTested Strategy:")
    final_port.printReport()
    print("\nNota bene, se il NetValue finale e' inferiore a initial_capital + Dividendi, di fatto c'e' stata una perdita sul capitale")
    print("Se nell'ultimo giorno, il totale delle tasse si abbassa, di fatto si sta scontando un Tax Credit Futuro\n")
    print(final_port.por_history.loc[datetime.datetime.combine(end_date - BDay(1), datetime.time.min)])
    # grandezze medie e minime

    print("\nAverages:")
    print("\nBenchmark Strategy")
    print(benchmark.por_history.mean())
    print("\nTested Strategy:")
    print(final_port.por_history.mean())
    print("\nMins:")
    print("\nBenchmark Strategy")
    print(benchmark.por_history.min())
    print("\nTested Strategy:")
    print(final_port.por_history.min())
    print("\nExecuted Tx: ")
    for t in final_port.executedTransactions:
        if t.verb == "BUY" or t.verb == "SELL":
            print(" Tx: " + str(t))

    # print(final_port.por_history)
    # final_port.por_history.plot(kind='line', y='NetValue')
    final_port.por_history['NetValue'].plot(kind='line', label="Custom", legend=True)

    NetValue_sma_short = final_port.por_history['NetValue'].rolling(window=20).mean()
    final_port.por_history['NetValue_sma_short'] = NetValue_sma_short
    final_port.por_history['NetValue_sma_short'].plot(kind='line', label="Custom_SMA_20", legend=True)

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
