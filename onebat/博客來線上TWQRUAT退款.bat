@echo off
:: 切換至正確的工作目錄
cd /d "C:\webtest"

title TWQR 線下測試工具 (UAT)

echo =======================================
echo [1/2] 執行：查詢交易 (Query Trade)
echo =======================================
node bookjumpquerytradeUAT.js

echo.
echo ---------------------------------------
echo 查詢完成，準備執行退款流程...
echo ---------------------------------------
echo.

echo =======================================
echo [2/2] 執行：退款程序 (Refund)
echo =======================================
node bookjumprefundUAT.js

echo.
echo =======================================
echo 任務已全部結束。
pause