from pandas_datareader import data as pdr
import requests_cache
import datetime
import arrow as ar

# cosa ho imparato?
# che il tipo indice del Dataframe ritornato è di tipo datetime... se aggiungo solo con date faccio casino...


print("\n\n*********************************\n")

expire_after = datetime.timedelta(days=3)
session = requests_cache.CachedSession(cache_name='./data/cache2', backend='sqlite', expire_after=expire_after)


start_date = datetime.date(2020, 5, 7)
end_date = datetime.date(2020, 5, 13)

df1 = pdr.DataReader("AMP.MI", "yahoo", start_date, end_date, session=session)

print(df1)
print("\n")

temp = None
last_raw = None
for dd in ar.Arrow.range('day', datetime.datetime.combine(start_date, datetime.time.min),
                                     datetime.datetime.combine(end_date, datetime.time.min)):
    print("Trying " + str(dd.date()))
    tried = False # devo provare 2 volte, una come date e una come datetime
    try:
        t = datetime.datetime.combine(dd.date(), datetime.time.min)
        temp = df1.loc[t]
        print("found first try")
        last_row = temp
    except KeyError as e:
        if not tried:
            tried = True
            try:
                temp = df1.loc[dd.date(), :]
                print("found second try")
                last_row = temp
            except KeyError as e:
                print("Adding new row " + str(dd.date()))
                t = datetime.datetime.combine(dd.date(), datetime.time.min)
                df1.loc[t] = last_row
                continue

print("\n")
print(df1)
print("\n")
print(df1.index)

#verifico che cambiando un valore in una riga non incasino gli altri...
dayAdded=datetime.date(2020,5,9)
t = datetime.datetime.combine(dayAdded, datetime.time.min)
print (df1.loc[t, 'Volume'])
#exit(0)
df1.loc[t, 'Volume'] = 0.0

df2 = df1.sort_index()
print(df2)

