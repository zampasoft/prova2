import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
import datetime
from pandas.tseries.offsets import BDay
from pandas_datareader import data as pdr
import pandas as pd
import matplotlib.pyplot as plt

end_date = datetime.date.today() + BDay(0)
symbols = ["UCG.MI", "LDO.MI", "NEXI.MI", "DOCU", "COTY", "TWLO", "GES", "TEAM", "MED", "NFLX", "BRBY.L", "AMZN", "GRPN", "ETSY", "GOOGL", "NOW", "MSFT", "DIS", "HSBA.L", "G.MI", "EL.PA", "CERV.MI", "ESNT.L", "VVD.F", "CVX", "MCRO.L"]

outcomes = pd.DataFrame(None, columns=['Symbol', 'slope', 'X^2'])
samples = 60

for sym in symbols:
    # print("Processing " + sym)
    data = pdr.DataReader(sym, "yahoo", end_date - BDay(samples), end_date)
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
    outcomes = outcomes.append({'Symbol': sym, 'slope': slope, 'X^2': x2}, ignore_index=True)
    # print('slope for ' + sym +':', model.coef_)
    # y_pred = model.predict(x)
    # print('predicted response:', y_pred, sep='\n')
print(outcomes.sort_values(by='slope', ascending=False))

# Plot Twilio
symbol='NFLX'
data = pdr.DataReader(symbol, "yahoo", end_date - BDay(samples), end_date)
x = np.array(range(len(data['Close']))).reshape((-1, 1))
y = list(data['Close'])
model = LinearRegression().fit(x, y)
model_degree = 5
x_ = PolynomialFeatures(degree=model_degree, include_bias=False).fit_transform(x)
poly_model = LinearRegression().fit(x_, y)

plt.scatter(x, y, edgecolor='b', s=20, label="Samples")
plt.plot(x, model.predict(x), label="Degree 1")
plt.plot(x, poly_model.predict(x_), label="Degree " + str(model_degree))
plt.legend(loc="best")
plt.title(symbol)
plt.show()
