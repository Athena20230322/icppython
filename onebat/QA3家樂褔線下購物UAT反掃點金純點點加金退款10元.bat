@echo off
chcp 65001 > nul
title 家樂福 UAT 自動化測試一鍵執行

:: --- [路徑設定] ---
set LOG_FILE=C:\webtest\refund_history_log.txt
set RESULT_FILE=C:\webtest\marketpaymentrefund.txt

echo ======================================================================
echo 測試開始時間: %date% %time%
echo 所有退款序號將紀錄至: %LOG_FILE%
echo ======================================================================

:: ==========================================
:: 第一組：純金 (Pure Cash)
:: ==========================================
echo [1/3] 正在執行：家樂褔登入付款 UAT (純金)

:: Step 1: 登入
python "C:\icppython\run_logincarrefourpay.py"
if %errorlevel% neq 0 (echo [錯誤] Step 1 失敗 && pause && exit /b)

:: Step 2: 讀取條碼付款
pushd C:\webtest
node carrefourUATreadbarcode.js
popd
if %errorlevel% neq 0 (echo [錯誤] Step 2 失敗 && pause && exit /b)

:: Step 3: 退款
call "C:\onebat\家樂褔線下購物UAT反掃退款.bat"

:: --- 紀錄序號 ---
<nul set /p ="[純金] %date% %time% | " >> "%LOG_FILE%"
type "%RESULT_FILE%" | findstr "OPRefundSeq" >> "%LOG_FILE%"

echo 第一組執行完成。
echo ----------------------------------------------------------------------

:: ==========================================
:: 第二組：點+金 (Points + Cash)
:: ==========================================
echo [2/3] 正在執行：家樂褔登入付款 UAT (點+金)

:: Step 1
python "C:\icppython\run_logincarrefourpaycashandop.py"
if %errorlevel% neq 0 (echo [錯誤] Step 1 失敗 && pause && exit /b)

:: Step 2
pushd C:\webtest
node carrefourUATreadbarcode.js
popd
if %errorlevel% neq 0 (echo [錯誤] Step 2 失敗 && pause && exit /b)

:: Step 3
call "C:\onebat\家樂褔線下購物UAT反掃退款.bat"

:: --- 紀錄序號 ---
<nul set /p ="[點+金] %date% %time% | " >> "%LOG_FILE%"
type "%RESULT_FILE%" | findstr "OPRefundSeq" >> "%LOG_FILE%"

echo 第二組執行完成。
echo ----------------------------------------------------------------------

:: ==========================================
:: 第三組：純點 (Pure Points)
:: ==========================================
echo [3/3] 正在執行：家樂褔登入付款 UAT (純點)

:: Step 1
python "C:\icppython\run_logincarrefourpayonlyop.py"
if %errorlevel% neq 0 (echo [錯誤] Step 1 失敗 && pause && exit /b)

:: Step 2
pushd C:\webtest
node carrefourUATreadbarcode.js
popd
if %errorlevel% neq 0 (echo [錯誤] Step 2 失敗 && pause && exit /b)

:: Step 3
call "C:\onebat\家樂褔線下購物UAT反掃退款.bat"

:: --- 紀錄序號 ---
<nul set /p ="[純點] %date% %time% | " >> "%LOG_FILE%"
type "%RESULT_FILE%" | findstr "OPRefundSeq" >> "%LOG_FILE%"

echo ======================================================================
echo 所有 UAT 測試程序執行完畢！
echo 請查看 Log 檔案確認退款序號。
pause