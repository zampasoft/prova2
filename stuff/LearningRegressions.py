import numpy as np
from sklearn.linear_model import LinearRegression
import datetime
from pandas.tseries.offsets import BDay
from pandas_datareader import data as pdr
import pandas as pd

end_date = datetime.date.today() + BDay(0)
symbols = ["UCG.MI", "LDO.MI", "NEXI.MI", "DOCU", "COTY", "TWLO", "GES", "TEAM", "MED", "NFLX", "BRBY.L", "AMZN", "GRPN", "ETSY", "GOOGL", "NOW", "MSFT", "DIS", "HSBA.L", "G.MI", "EL.PA", "CERV.MI", "ESNT.L", "VVD.F"]

outcomes = pd.DataFrame(None, columns=['Symbol', 'slope'])

for sym in symbols:
    # print("Processing " + sym)
    data = pdr.DataReader(sym, "yahoo", end_date - BDay(20), end_date)
    # print(data)
    x = np.array(range(len(data['Close']))).reshape((-1, 1))
    # print(x)
    y = list(data['Close'])
    # print(y)
    model = LinearRegression().fit(x, y)
    # r_sq = model.score(x, y)
    # print('coefficient of determination:', r_sq)
    # print('intercept:', model.intercept_)
    slope = model.coef_
    outcomes = outcomes.append({'Symbol': sym, 'slope': slope}, ignore_index=True)
    # print('slope for ' + sym +':', model.coef_)
    # y_pred = model.predict(x)
    # print('predicted response:', y_pred, sep='\n')
print(outcomes.sort_values(by='slope', ascending=False))
