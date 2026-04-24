@echo off
title 自動化測試執行腳本 (精簡紀錄)
chcp 65001 >nul

:: 定義紀錄檔路徑
set LOG_FILE=C:\webtest\refund_history_log.txt

echo ==================================================
echo [1/3] 開始執行：超商支付 (Python)
python "C:\icppython\run_login711paycashandOP.py"
if %errorlevel% neq 0 pause

echo.
echo ==================================================
echo [2/3] 開始執行：超商SIT 部分點+金 付款 (Node.js)
node "c:\webtest\marketpaymentautocashandop.js"
if %errorlevel% neq 0 pause

echo.
echo ==================================================
echo [3/3] 開始執行：超商SIT 部份點+金 退款 (Node.js)
echo --------------------------------------------------

:: --- 修改重點：只擷取 OPRefundSeq 並加上時間 ---
:: 1. 先把時間寫入 Log (不換行，讓序號接在後面)
<nul set /p ="執行時間: %date% %time% | " >> "%LOG_FILE%"

:: 2. 執行程式，並透過 findstr 只抓取包含 OPRefundSeq 的那一行追加進 Log
node "c:\webtest\marketpaymentrefundauto.js" | findstr "OPRefundSeq" >> "%LOG_FILE%"

:: 3. 如果沒抓到 (例如程式出錯)，補一個換行符號
echo. >> "%LOG_FILE%"
:: --------------------------------------------

if %errorlevel% neq 0 pause

echo.
echo ==================================================
echo 執行完畢！序號已存入: %LOG_FILE%
echo ==================================================
pause