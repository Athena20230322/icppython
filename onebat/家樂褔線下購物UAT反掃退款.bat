@echo off
title 家樂線下反掃退款自動化腳本
color 0B

echo ======================================================
echo           正在啟動：家樂線下反掃退款程序
echo ======================================================
echo.

:: 切換到工作目錄
cd /d C:\webtest

:: 執行第一個腳本：查詢交易
echo [步驟 1/2] 正在執行查詢交易 (carrefourjumpquerytradeUAT.js)...
call node carrefourjumpquerytradeUAT.js

echo.
echo ------------------------------------------------------
echo 查詢完成，準備執行退款...
echo ------------------------------------------------------
echo.

:: 執行第二個腳本：退款程序
echo [步驟 2/2] 正在執行退款程序 (carrefourrefundUAT.js)...
call node carrefourrefundUAT.js

echo.
echo ======================================================
echo           所有程序執行完畢！
echo ======================================================
echo.

pause