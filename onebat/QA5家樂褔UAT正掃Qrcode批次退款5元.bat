@echo off
title 家樂福批次退款自動化腳本
color 0b

:: 強制切換到工作目錄
cd /d "C:\webtest"

echo ==================================================
echo   開始執行：家樂福批次查詢與退款流程
echo   工作目錄: %cd%
echo   執行時間: %date% %time%
echo ==================================================
echo.

:: 第一步：執行查詢與產生交易明細
echo [步驟 1/2] 正在讀取 Excel 並查詢交易明細...
node carrefourjumpquerytradeUATICPOexcel.js
if %errorlevel% neq 0 (
    echo.
    echo [錯誤] 步驟 1 查詢過程發生問題，終止後續動作。
    pause
    exit /b %errorlevel%
)

echo.
echo --------------------------------------------------
echo [步驟 1 完成] 交易明細已成功更新。
echo --------------------------------------------------
echo.

:: 第二步：執行退款
echo [步驟 2/2] 正在根據查詢結果處理退款...
node carrefourrefundUATICPObatch.js
if %errorlevel% neq 0 (
    echo.
    echo [錯誤] 步驟 2 退款過程發生問題。
    pause
    exit /b %errorlevel%
)

echo.
echo ==================================================
echo   恭喜！所有批次處理已順利完成。
echo ==================================================
echo.
pause