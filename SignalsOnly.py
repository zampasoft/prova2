# ver 1.0
import datetime
import logging
import os
import sim_trade
import arrow as ar


if __name__ == "__main__":
    # cominciamo a lavorare
    print("\nStarting...")
    # setting up Logging
    try:
        os.remove("./logs/signals.log")
    except Exception as e:
        print(e)
    logging.basicConfig(filename='./logs/signals.log', level=logging.DEBUG)
    #logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
    logging.info("******************************************************")
    logging.info("*      NEW START : " + str(datetime.datetime.now()) + "        *")
    logging.info("******************************************************")

    # Last day
    end_date = datetime.date.today()
    # end_date = datetime.date(2020, 6, 5)
    # First day
    start_date = datetime.date(2019, 6, 5)
    initial_capital = 500000.0  # EUR

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
    # devo definire una strategia di Trading
    print("\tCalculating Signals")
    my_trading_strategy = sim_trade.InvBollbandsStrategy(myPortfolio)
    #my_trading_strategy = sim_trade.BuyAndHoldTradingStrategy(myPortfolio)
    # calcolo i segnali BUY e SELL
    timestamp = datetime.datetime.now()
    logging.info("\nCalculating BUY/SELL Signals")
    my_strategy_signals = my_trading_strategy.calc_suggested_transactions(sell_all=False, w_short=1.0, w_long=1.0)
    logging.info("Signals calculated in " + str(datetime.datetime.now() - timestamp))

    print("Calculation Outcome:")

    print("\nSignalled Tx: ")
    for dd in ar.Arrow.range('day', datetime.datetime.combine(start_date, datetime.time.min),
                             datetime.datetime.combine(end_date, datetime.time.min)):
        for t in my_strategy_signals[dd.date()]:
            if t.verb == "BUY" or t.verb == "SELL":
                print(" Tx: " + str(t))

    # elaborazione finita visualizziamo l'outcome
    print("\nEnded, please check log file.\n")



