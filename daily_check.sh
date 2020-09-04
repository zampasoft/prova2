#!/bin/bash

cd  /home/nemofox/PycharmProjects/BackTesting
rm /home/nemofox/PycharmProjects/BackTesting/data/*

python3 SignalsOnly.py

while [ $? -ne 0 ]; do
	sqlite3  data/cache.sqlite 'delete from responses ORDER BY rowid DESC LIMIT 10;'
        # sqlitebrowser data/cache.sqlite
	python3 SignalsOnly.py
done

echo " "
echo "checking logs/backtesting.log"
grep retrieved logs/backtesting.log
echo " "
echo "checking logs/signals.log"
grep retrieved logs/signals.log
