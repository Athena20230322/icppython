@echo off
:: 切換到工作目錄
cd /d C:\webtest

echo [1/2] 正在執行：讀取 Excel 並查詢單號...
node donutSITreadbarcodeICPOexcel.js

echo.
echo -----------------------------------------
echo [2/2] 正在執行：批次處理交易...
node donutrefundSITreadbarcodeICPObatch.js

echo.
echo -----------------------------------------
echo 所有處理已完成！
pause