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
    signalsOnly = False
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

    # Last day
    end_date = datetime.date.today() + BDay(1)
    # end_date = datetime.date(2019, 6, 28) + BDay(0)
    # First day
    start_date = datetime.date(2016, 1, 12) + BDay(0)
    # start_date = datetime.date(2020, 10, 28) + BDay(0)
    long_stats = 150
    short_stats = 20
    initial_capital = 100000.0  # 100.000 EUR
    sell_all = False


    filename = "./data/saved.mkts.data." + str(start_date.date()) + '-' + str(end_date.date())
    try:
        # se esiste questo file, lo carico e risparmio qualche minuto
        file_handle = open(filename, "rb")
        print("Loading previously saved Initial Portfolio and quotations")
        logging.info("\nLoading previously saved Initial Portfolio and quotations from: " + str(file_handle.name))
        myPortfolio = pickle.load(file_handle)
        file_handle.close()
    except FileNotFoundError:
        # Create and Initialise myPortfolio
        myPortfolio = sim_trade.Portfolio(start_date, end_date, initial_capital, days_short=short_stats, days_long=long_stats)
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
        myPortfolio.calc_stats()
        print("\tFixing Data")
        myPortfolio.fix_history_data()
        # mi salvo il calcolo per velocizzare i miei tests
        file_handle = open(filename, "wb")
        logging.info("\nSaving Initial Portfolio and quotations to: " + str(file_handle.name))
        pickle.dump(myPortfolio, file_handle)
        file_handle.close()
    # devo definire una strategia di Trading
    top_strategy = sim_trade.InvBollbandsStrategy(myPortfolio)
    print("\tCalculating Signals for " + top_strategy.description)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_signals = top_strategy.calc_suggested_transactions(sell_all=sell_all, initial_buy=True, w_short=3.0, w_long=1.0)
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))
    # Printing raw Signals
    print("Calculation Outcome:")
    print("\nSignalled Tx: ")
    for dd in pd.date_range(start=start_date, end=end_date, freq='B'):
        for t in my_strategy_signals[dd]:
            if t.verb == "BUY" or t.verb == "SELL":
                print(" Tx: " + str(t))

    if signalsOnly:
        # se voglio solo i segnali posso finire qui
        exit(0)

    # processo tutte le transazioni pending e vedo cosa succede
    timestamp = datetime.datetime.now()
    logging.info("\nExecuting trades")
    print("\tSimulating trading")
    top_port = top_strategy.runTradingSimulation(max_orders=25)
    logging.info("Trades completed in " + str(datetime.datetime.now() - timestamp))

    print("\n" + top_port.description + " Executed Tx: ")
    for t in top_port.executedTransactions:
        if t.verb == "BUY" or t.verb == "SELL":
            print(" Tx: " + str(t))

    # calculating base case
    base_strat = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
    # base_strat = sim_trade.InvBollbandsStrategy(myPortfolio)
    # base_strat = sim_trade.BollbandsStrategy(myPortfolio)
    print("\nCalculating " + base_strat.description)
    base_signals = base_strat.calc_suggested_transactions(sell_all=sell_all, initial_buy=True)
    base_port = base_strat.runTradingSimulation(max_orders=24.5)
    # base_port.por_history['NetValue'].plot(kind='line', label=base_port.description, legend=True)
    print("\n" + base_port.description + " Executed Tx: ")
    for t in base_port.executedTransactions:
        if t.verb == "BUY" or t.verb == "SELL":
            print(" Tx: " + str(t))

    # calculating second benchmark
    # my_strategy = sim_trade.BollbandsStrategy(myPortfolio)
    # my_strategy = sim_trade.InvBollbandsStrategy(myPortfolio)
    my_strategy = sim_trade.CustomStrategy(myPortfolio)
    print("\nCalculating " + my_strategy.description)
    my_signals = my_strategy.calc_suggested_transactions(sell_all=sell_all, initial_buy=True)
    my_port = my_strategy.runTradingSimulation(max_orders=25.5)
    print("\n" + my_port.description + " Executed Tx: ")
    for t in my_port.executedTransactions:
        if t.verb == "BUY" or t.verb == "SELL":
            print(" Tx: " + str(t))
    # TODO: bisognerebbe stampare una tabella che confronti gli esiti finali, medi e minimi delle tre strategie

    simulations = [top_port, my_port, base_port]
    simul_outcomes = pd.DataFrame(None, columns=['Simulation Strategy', 'Average Net Value', 'Final Liquidity', 'TotalCommissions', 'TotalDividens',
                                       'TotalTaxes'])
    print("\nSimulations Outcome:\n")
    for simul in simulations:
        assert isinstance(simul, sim_trade.Portfolio), "Coding error... check Simulations list"
        simul.por_history.loc[start_date:, 'NetValue'].plot(kind='line', label=simul.description, legend=True)
        # simul.por_history['TotalTaxes'].plot(kind='line', label=simul.description, legend=True)
        new_row = {'Simulation Strategy': simul.description, 'Average Net Value': simul.por_history.loc[start_date:, 'NetValue'].mean(), 'Final Liquidity': simul.por_history.loc[end_date, 'Liquidity'], 'TotalCommissions': simul.por_history.loc[end_date, 'TotalCommissions'], 'TotalDividens': simul.por_history.loc[end_date, 'TotalDividens'], 'TotalTaxes': simul.por_history.loc[end_date, 'TotalTaxes']}
        simul_outcomes = simul_outcomes.append(new_row, ignore_index=True)
    pd.set_option("display.max_rows", None, "display.max_columns", None, "display.width", 1000)
    print(simul_outcomes.sort_values(by='Average Net Value', ascending=False))
    plt.show()
    print("\nEnded, please check log file.\n")
