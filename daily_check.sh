#!/bin/bash

let MAX_RETRIES=10
let TRIES=0

BASE_DIR=$(dirname $0)
echo ${BASE_DIR}



cd ${BASE_DIR}
rm ${BASE_DIR}/data/*



python3 backtest.py

while [ $? -ne 0 ] && [ $TRIES -lt $MAX_RETRIES ]; do
	mv ${BASE_DIR}/logs/backtesting.log ${BASE_DIR}/logs/backtesting.log.old.$TRIES
	let TRIES=$TRIES+1
	sqlite3  ./data/cache.sqlite 'delete from responses ORDER BY rowid DESC LIMIT 10;'
        # sqlitebrowser data/cache.sqlite
	python3 backtest.py	
done

exit

echo " "
echo "checking logs/backtesting.log"
grep retrieved ${BASE_DIR}/logs/backtesting.log
