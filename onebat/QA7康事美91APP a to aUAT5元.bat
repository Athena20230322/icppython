@echo off
:: 設定編碼為 UTF-8 以支援中文顯示
CHCP 65001 > nul
cd /d C:\webtest

:: 設定 Log 檔案路徑（方便管理）
set LOG_FILE=C:\webtest\test_result_log.txt

echo ========================================
echo [%date% %time%] 執行測試自動化開始 >> %LOG_FILE%
echo ========================================

echo ======================================================
echo STEP 1: 執行 91APP 交易查詢 (cosmed91appquerytradeUAT.js)
echo ======================================================
:: 執行並同時顯示在螢幕上，且追加到 Log
echo [STEP 1 查詢開始] >> %LOG_FILE%
node cosmed91appquerytradeUAT.js >> %LOG_FILE%

:: 檢查上一支程式是否成功執行 (如果 node 回傳錯誤碼則停止)
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 查詢程式執行失敗，停止後續退款作業。
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================
echo STEP 2: 執行 91APP 退款作業 (cosmed91apprefundUAT.js)
echo ======================================================
echo [STEP 2 退款開始] >> %LOG_FILE%
node cosmed91apprefundUAT.js >> %LOG_FILE%

echo. >> %LOG_FILE%
echo ---------------------------------------- >> %LOG_FILE%
echo 執行完畢時間: %date% %time% >> %LOG_FILE%
echo ---------------------------------------- >> %LOG_FILE%

echo.
echo ----------------------------------------
echo 所有測試流程執行完畢！結果已寫入 %LOG_FILE%
pause