from pandas_datareader import data as pdr
import pandas as pd
import requests_cache
import datetime

# cosa ho imparato?
# che il tipo indice del Dataframe ritornato è di tipo datetime... se aggiungo solo con date faccio casino...


print("\n\n*********************************\n")

expire_after = datetime.timedelta(days=3)
session = requests_cache.CachedSession(cache_name='../data/cache2', backend='sqlite', expire_after=expire_after)


start_date = datetime.date(2020, 5, 7)
end_date = datetime.date(2020, 5, 13)

df1 = pdr.DataReader("AMP.MI", "yahoo", start_date, end_date, session=session)
my_index = pd.date_range(start=start_date, end=end_date)

print(my_index)
print("\n")
print(df1)
print("\n")

# using my_index
temp = None
last_raw = None
for dd in my_index:
    print("Trying " + str(dd.date()))
    try:
        temp = df1.loc[dd]
        print("found first try")
        last_row = temp
    except KeyError as e:
        print("Adding new row " + str(dd.date()))
        df1.loc[dd] = last_row
        continue

print("\n")
print(df1)
print("\n")
print(df1.index)

df2 = df1.sort_index()
print(df2)


# verifico che cambiando un valore in una riga non incasino gli altri...
dayAdded = datetime.date(2020, 5, 9)
t = datetime.datetime.combine(dayAdded, datetime.time.min)
print(df1.loc[t, 'Volume'])
# exit(0)
df1.loc[t, 'Volume'] = 0.0

df2 = df1.sort_index()
print(df2)

