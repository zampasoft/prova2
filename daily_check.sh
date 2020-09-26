#!/bin/bash

cd  /home/nemofox/PycharmProjects/BackTesting
rm /home/nemofox/PycharmProjects/BackTesting/data/*

let MAX_RETRIES=10
let TRIES=0
python3 SignalsOnly.py

while [ $? -ne 0 ] && [ $TRIES -lt $MAX_RETRIES ]; do
	let TRIES=$TRIES+1
	sqlite3  data/cache.sqlite 'delete from responses ORDER BY rowid DESC LIMIT 10;'
        # sqlitebrowser data/cache.sqlite
	# python3 SignalsOnly.py	
	python3 backtest.py	
done

exit

echo " "
echo "checking logs/backtesting.log"
grep retrieved logs/backtesting.log
echo " "
echo "checking logs/signals.log"
grep retrieved logs/signals.log
