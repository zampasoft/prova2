# Import the necessary packages and modules
#import matplotlib
#import numpy as np
import matplotlib.pyplot as plt
import datetime
import pandas as pd

data = {'Date': [datetime.date(2020,5,23), datetime.date(2020,5,24), datetime.date(2020,5,25)], 'Liquidity': [100000.0, 90000.0, 110000.0], 'NetValue': [100000.0, 90000.0, 110000.0],
        'TotalCommissions': [0.0, 5000.0, 8000.0], 'TotalDividens': [0.0, 0.0, 0.0], 'TotalTaxes': [0.0, 5000.0, 20000]}
temp = pd.DataFrame(data, columns=['Date', 'Liquidity', 'NetValue', 'TotalCommissions', 'TotalDividens',
                                   'TotalTaxes'])
temp['Date'] = pd.to_datetime(temp['Date'])
por_history = temp.set_index('Date')

por_history['NetValue'].plot()
plt.show()