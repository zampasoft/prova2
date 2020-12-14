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

# end_date = datetime.date.today() + BDay(0)
end_date = datetime.date(2019, 10, 31) + BDay(0)
symbols = []
# symbols = ["COTY", "NKLA", "TSLA", "MRNA", "BT-A.L", "SFL.MI", "BA", "AAL", "UCG.MI", "LDO.MI", "DOCU", "TWLO", "GES", "TEAM", "NFLX", "BRBY.L", "AMZN", "GRPN", "ETSY", "GOOGL", "NOW", "MSFT", "DIS", "HSBA.L", "G.MI", "EL.PA", "CERV.MI", "ESNT.L", "VVD.F", "CVX", "MCRO.L"]
AssetsInScopeCSV = "../sim_trade/AssetsInScope.csv"
with open(AssetsInScopeCSV, newline='') as csvfile:
    csvreader = csv.reader(csvfile, dialect='excel')
    first_row = True
    for row in csvreader:
        if first_row:
            first_row = False
        else:
            symbols.append(row[0])

print(symbols)

expire_after = datetime.timedelta(days=3)
session = requests_cache.CachedSession(cache_name='../data/cache2.sqlite', backend='sqlite', expire_after=expire_after)

outcomes = pd.DataFrame(None, columns=['Symbol', 'slope', 'XSQ'])
# per capire se un titolo ha iniziato a crescere guado 20 campioni, per capire se il massimo è superato 60?
samples = 250

for sym in symbols:
    print("Loading " + sym, end="", flush=True)
    try:
        data = pdr.DataReader(sym, "yahoo", end_date - BDay(samples), end_date, session=session)
    except:
        print("...Failed")
        continue
    print("...OK")
    # print(data)
    x = np.array(range(len(data['Close']))).reshape((-1, 1))
    # print(x)
    y = list(data['Close'])
    # print(y)
    model = LinearRegression().fit(x, y)
    # r_sq = model.score(x, y)
    # print('coefficient of determination:', r_sq)
    # print('intercept:', model.intercept_)
    slope = model.coef_[0] * 100 / model.intercept_
    # now looking at a second degree polynomail regression
    # create e new Input with x and x^2
    x_ = PolynomialFeatures(degree=2, include_bias=False).fit_transform(x)
    # print(y)
    y1 = np.array(y)*(100/model.intercept_)
    # print(y1)
    poly_model = LinearRegression().fit(x_, y1)
    # r_sq = poly_model.score(x_, y)
    # print('coefficient of determination:', r_sq)
    # print('intercept:', poly_model.intercept_)
    # print('coefficients:', poly_model.coef_)
    x2 = poly_model.coef_[1]
    outcomes = outcomes.append({'Symbol': sym, 'slope': slope, 'XSQ': x2}, ignore_index=True)
    # print('slope for ' + sym +':', model.coef_)
    # y_pred = model.predict(x)
    # print('predicted response:', y_pred, sep='\n')
pd.set_option('display.max_rows', None)
print(outcomes.sort_values(by='slope', ascending=False))
print()

# Plot stock whith lowest XSQ
# symbol = str(outcomes[outcomes.slope == outcomes.slope.min()]['Symbol'].iloc[0])
# symbol = str(outcomes[outcomes.slope == outcomes.slope.max()]['Symbol'].iloc[0])
symbol = 'LSE.L'
print("Plotting: " + symbol)
data = pdr.DataReader(symbol, "yahoo", end_date - BDay(samples), end_date)
x = np.array(range(len(data['Close']))).reshape((-1, 1))
y = list(data['Close'])
model = LinearRegression().fit(x, y)
model_degree = 3
x_ = PolynomialFeatures(degree=model_degree, include_bias=False).fit_transform(x)
poly_model = LinearRegression().fit(x_, y)

plt.scatter(x, y, edgecolor='b', s=20, label="Samples")
plt.plot(x, model.predict(x), label="Degree 1")
plt.plot(x, poly_model.predict(x_), label="Degree " + str(model_degree))
plt.legend(loc="best")
plt.title(symbol)
plt.show()
