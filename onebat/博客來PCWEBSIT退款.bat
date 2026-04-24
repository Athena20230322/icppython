@echo off
CHCP 65001 > nul
cd /d C:\webtest

echo ========================================
echo STEP 1: 執行交易查詢 (bookwebquerytradeSIT.js)
echo ========================================
node bookwebquerytradeSIT.js

echo.
echo ========================================
echo STEP 2: 執行退款作業 (bookwebrefundSIT.js)
echo ========================================
node bookwebrefundSIT.js

echo.
echo ----------------------------------------
echo 所有測試流程執行完畢！
pause