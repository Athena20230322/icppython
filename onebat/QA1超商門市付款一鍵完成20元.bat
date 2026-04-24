@echo off
title 自動執行測試腳本 (紀錄至 Log)
chcp 65001 > nul

:: 設定 Log 檔案路徑
set LOG_FILE=C:\webtest\refund_history_log.txt

:: ==========================================
:: 第一組執行順序
:: ==========================================
echo [1/3] 正在開始執行第一組程式...

cd /d C:\icppython
python run_login711pay.py

cd /d C:\webtest
node marketpaymentauto.js

echo === 第一組退款測試紀錄 (%date% %time%) === >> "%LOG_FILE%"
node marketpaymentrefundauto.js >> "%LOG_FILE%"
echo ------------------------------------------ >> "%LOG_FILE%"

echo 第一組程式執行完畢，結果已存入 Log。
echo ------------------------------------------

:: ==========================================
:: 第二組執行順序
:: ==========================================
echo [2/3] 正在開始執行第二組程式...

cd /d C:\icppython
python run_login711payOP.py

cd /d C:\webtest
node marketpaymentauto.js

echo === 第二組退款測試紀錄 (%date% %time%) === >> "%LOG_FILE%"
node marketpaymentrefundauto.js >> "%LOG_FILE%"
echo ------------------------------------------ >> "%LOG_FILE%"

echo 第二組程式執行完畢，結果已存入 Log。
echo ------------------------------------------
echo 所有程序已執行完畢！
pause