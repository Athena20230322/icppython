@echo off
CHCP 65001 > nul
cd /d C:\webtest

:: 設定 Log 檔案路徑（方便管理）
set LOG_FILE=C:\webtest\test_result_log.txt

echo ========================================
echo [%date% %time%] 執行測試自動化開始 >> %LOG_FILE%
echo ========================================

echo ========================================
echo STEP 1: 執行交易查詢 (bookwebquerytradeUAT.js)
echo ========================================
:: 執行並同時顯示在螢幕上，且追加到 Log
echo [STEP 1 查詢開始] >> %LOG_FILE%
node bookwebquerytradeUAT.js >> %LOG_FILE%

echo.
echo ========================================
echo STEP 2: 執行退款作業 (bookwebrefundUAT.js)
echo ========================================
echo [STEP 2 退款開始] >> %LOG_FILE%
node bookwebrefundUAT.js >> %LOG_FILE%

echo. >> %LOG_FILE%
echo ---------------------------------------- >> %LOG_FILE%
echo 執行完畢時間: %date% %time% >> %LOG_FILE%
echo ---------------------------------------- >> %LOG_FILE%

echo.
echo ----------------------------------------
echo 所有測試流程執行完畢！結果已寫入 %LOG_FILE%
pause