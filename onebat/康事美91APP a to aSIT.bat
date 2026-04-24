@echo off
:: 設定編碼為 UTF-8 以支援中文顯示
CHCP 65001 > nul
cd /d C:\webtest

echo ======================================================
echo STEP 1: 執行 91APP 交易查詢 (cosmed91appquerytrade.js)
echo ======================================================
node cosmed91appquerytrade.js

:: 檢查上一支程式是否成功執行 (如果 node 回傳錯誤碼則停止)
if %ERRORLEVEL% NEQ 0 (
    echo [錯誤] 查詢程式執行失敗，停止後續退款作業。
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ======================================================
echo STEP 2: 執行 91APP 退款作業 (cosmed91apprefund.js)
echo ======================================================
node cosmed91apprefund.js

echo.
echo ------------------------------------------------------
echo ✅ 流程執行完畢！
echo ------------------------------------------------------
pause