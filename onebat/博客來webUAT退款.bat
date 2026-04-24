@echo off
title iCashPay 查詢與退款一鍵執行工具
chcp 65001 >nul

echo ========================================
echo   步驟 1: 執行查詢 (Query Trade)
echo ========================================
node C:\webtest\bookwebquerytradeUAT.js

echo.
echo ========================================
echo   步驟 2: 執行退款 (Refund Trade)
echo ========================================
node C:\webtest\bookwebrefundUAT.js

echo.
echo ========================================
echo   測試流程結束！
echo ========================================
pause