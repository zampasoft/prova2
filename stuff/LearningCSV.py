#
import csv
from datetime import datetime

filename = "./TestCSV.csv"

with open(filename, newline='') as csvfile:
    spamreader = csv.reader(csvfile, dialect='excel')
    first_row = True
    for row in spamreader:
        if first_row:
            print("TITLES")
            print(row)
            first_row = False
        else:
            # we expect DATE, VERB, SYMBOL
            dd = datetime.strptime(row[0], '%d/%m/%Y')
            verb = row[1]
            symbol = row[2]
            print(str(dd) + " " + str(verb) + " " + str(symbol))

