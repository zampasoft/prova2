# ver 1.0
import datetime
import logging
import os
import pandas as pd
import sim_trade

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
    myPortfolio.loadQuotations()
    logging.info("Retrieve completed in " + str(datetime.datetime.now() - timestamp))
    # adesso dovrei aver recuperato tutti i dati...
    # Devo sistemare i gap nelle date. Non posso farlo prima perché la natura multiThread delle librerie crea dei casini
    print("\tFixing Data")
    myPortfolio.fill_history_gaps()
    # possiamo cominciare a pensare a cosa fare...

    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    my_trading_strategy = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
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

    # elaborazione finita proviamo a visualizzare qualcosa
    print("\nEnded, please check log file.\n")
    print("Simulation Outcome:")
    print("\nInitial Portfolio")
    myPortfolio.printReport()
    print("\nFinal Portfolio:")
    final_port.printReport()
    print("\nNota bene, se il NetValue finale è inferiore a initial_capital + Dividendi, di fatto c'è stata una perdita sul capitale")
    print("Se nell'ultimo giorno, il totale delle tasse si abbassa, di fatto si sta scontando un Tax Credit Futuro\n")
    print(final_port.por_history.loc[end_date - datetime.timedelta(days=1)])
    print("\nExecuted Tx: ")
    for t in final_port.executedTransactions:
        print(" Tx: " + str(t))