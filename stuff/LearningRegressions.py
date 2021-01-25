import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import datetime
from pandas.tseries.offsets import BDay
from pandas_datareader import data as pdr
import pandas as pd
import matplotlib.pyplot as plt
import requests_cache
import csv
from multiprocessing.dummy import Pool as ThreadPool
import logging


def download_quotations(symbol):
    # global end_date
    # global start_date2
    # global session
    try:
        data = pdr.DataReader(symbol, "yahoo", start_date, end_date, session=session)
        print("Retrieved: " + symbol)
    except Exception as e:
        print("Quotations for: " + symbol + " could not be retrieved because of " + str(e))
        data = None
    return [symbol, data]


if __name__ == "__main__":
    # per capire se un titolo ha iniziato a crescere guado 20 campioni, per capire se il massimo è superato 60?
    samples = 20
    # logging.basicConfig(level=logging.DEBUG)
    # end_date = datetime.date.today() + BDay(1)
    end_date = datetime.date.today() + BDay(0)
    start_date = end_date - BDay(samples)
    # start_date = datetime.date(2020, 10, 28) + BDay(0)
    # end_date = datetime.date(2019, 10, 31) + BDay(0)
    symbols = []
    AssetsInScopeCSV = "../sim_trade/AssetsInScope.csv"
    with open(AssetsInScopeCSV, newline='') as csvfile:
        csvreader = csv.reader(csvfile, dialect='excel')
        first_row = True
        for row in csvreader:
            if first_row:
                first_row = False
            else:
                symbols.append(row[0])

    # reassign symbols if you want to analyse a subset of stocks
    # symbols = ["ILTY.MI", "AAL", "UCG.MI", "LDO.MI", "DOCU", "TWLO", "GES", "NOW", "TEAM", "NFLX", "BRBY.L", "AMZN", "GRPN", "ETSY", "GOOGL", "MSFT", "DIS", "HSBA.L", "AMRS", "EL.PA", "CERV.MI", "ESNT.L", "VVD.F", "CVX", "MCRO.L"]

    expire_after = datetime.timedelta(days=3)
    session = requests_cache.CachedSession(cache_name='../data/cache', backend='sqlite', expire_after=expire_after)

    outcomes = pd.DataFrame(None, columns=['Symbol', 'slope', 'XSQ'])

    # print details
    print("Number of samples: " + str(samples))
    print("Sort by: XSQ")
    print("Tickers to analyse: " + str(len(symbols)) + "\n")
    print("Checking for duplicates:")
    symbols_no_duplicates = []
    for sym in symbols:
        if sym in symbols_no_duplicates:
            print(sym + " is DUPLICATED")
            continue
        else:
            symbols_no_duplicates.append(sym)

    # recupero le quotazioni in multiThread
    start_timestamp = datetime.datetime.now()
    print("\nStart Downloading Quotations")
    pool = ThreadPool(20)
    results = pool.map(download_quotations, symbols_no_duplicates)
    end_timestamp = datetime.datetime.now()
    print("Elapsed: " + str(end_timestamp - start_timestamp))
    # print(results)
    print(str(len(results)) + " quotations retrieved")

    for sym, data in results:
        # print(data)
        x = np.array(range(len(data['Close']))).reshape((-1, 1))
        # print(x)
        y = list(data['Close'])
        # print(y)
        model = LinearRegression().fit(x, y)
        # r_sq = model.score(x, y)
        # print('coefficient of determination:', r_sq)
        # print('intercept:', model.intercept_)
        slope = model.coef_[0] * 100 / y[0]
        # now looking at a second degree polynomail regression
        # create e new Input with x and x^2
        x_ = PolynomialFeatures(degree=2, include_bias=False).fit_transform(x)
        # print(y)
        # sto assumendo che model.intercept_ sia positivo...
        y1 = np.array(y) * (100 / y[0])
        # print(y1)
        poly_model = LinearRegression().fit(x_, y1)
        # r_sq = poly_model.score(x_, y)
        # print('coefficient of determination:', r_sq)
        # print('intercept:', poly_model.intercept_)
        # print('coefficients:', poly_model.coef_)
        x2 = poly_model.coef_[1]
        ## x2 = poly_model.coef_
        outcomes = outcomes.append({'Symbol': sym, 'slope': slope, 'XSQ': x2}, ignore_index=True)
        # print('slope for ' + sym +':', model.coef_)
        # y_pred = model.predict(x)
        # print('predicted response:', y_pred, sep='\n')

    pd.set_option('display.max_rows', None)
    print("\n")
    print(outcomes.sort_values(by='slope', ascending=False))
    print()

    # Plot stock whith lowest XSQ
    # symbol = str(outcomes[outcomes.XSQ == outcomes.XSQ.min()]['Symbol'].iloc[0])
    symbol = str(outcomes[outcomes.slope == outcomes.slope.min()]['Symbol'].iloc[0])
    symbol = 'F'
    print("Plotting: " + symbol)
    data = pdr.DataReader(symbol, "yahoo", start_date, end_date, session=session)
    x = np.array(range(len(data['Close']))).reshape((-1, 1))
    y = list(data['Close'])
    model = LinearRegression().fit(x, y)
    model_degree = 3
    x_ = PolynomialFeatures(degree=model_degree, include_bias=False).fit_transform(x)
    poly_model = LinearRegression().fit(x_, y)
    # print(poly_model.coef_)

    plt.scatter(x, y, edgecolor='b', s=20, label="Samples")
    plt.plot(x, model.predict(x), label="Degree 1")
    plt.plot(x, poly_model.predict(x_), label="Degree " + str(model_degree))
    plt.legend(loc="best")
    plt.title(symbol)
    plt.show()
