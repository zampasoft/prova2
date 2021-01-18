#!/bin/bash

SOURCE_DIR=/home/nemofox/PycharmProjects/BackTesting
TARGET_DIR=ubuntu@cloudvm:/home/ubuntu/TradingAdvice

#mv ${TARGET_DIR}/daily_check.sh ${TARGET_DIR}/daily_check.sh.old
scp ${SOURCE_DIR}/daily_check.sh ${TARGET_DIR}/

#mv ${TARGET_DIR}/backtest.py ${TARGET_DIR}/backtest.py.old
scp ${SOURCE_DIR}/backtest.py ${TARGET_DIR}/

#mv ${TARGET_DIR}/sim_trade/__init__.py ${TARGET_DIR}/sim_trade/__init__.py.old
scp ${SOURCE_DIR}/sim_trade/__init__.py ${TARGET_DIR}/sim_trade/

#mv ${TARGET_DIR}/sim_trade/myTransactions.csv ${TARGET_DIR}/sim_trade/myTransactions.csv.old
scp ${SOURCE_DIR}/sim_trade/myTransactions.csv ${TARGET_DIR}/sim_trade/

#mv ${TARGET_DIR}/sim_trade/AssetsInScope.csv ${TARGET_DIR}/sim_trade/AssetsInScope.csv.old
scp ${SOURCE_DIR}/sim_trade/AssetsInScope.csv ${TARGET_DIR}/sim_trade/

echo "Done!"

