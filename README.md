icppython
本專案為 iCash Pay (ICP) 相關 API 的 Python 自動化測試腳本。

🚀 主要功能腳本
腳本檔案

功能說明

run_icplogin.py

執行登入流程，並在完成後產出 API 測試報告。

run_icpaccountclose.py

執行結清帳號流程，執行後將直接結清指定帳號。

full_registration_flow.py

(SIT 環境) 提供一鍵化註冊本國人會員的完整流程。

master_nextstep_runner.py

用於執行註冊後不同 NextStep 狀態的接續流程，支援以下狀態：<br>- Next1, Next2, Next4, Next5, Next6, Next9, Next13

📁 目錄說明
icploginapireport/: 用於存放 run_icplogin.py 執行後所產出的 HTML 測試報告。

📋 API 執行流程
ICP 本國人註冊 API 執行順序
此流程由 full_registration_flow.py 完整執行。

M0003_01 - 設定註冊資訊

M0007 - 發送簡訊驗證碼

M0010 - 驗證簡訊

M0004 - 身分驗證

M0012 - 變更交易密碼

M0149 - 檢查是否為 OP 會員

M0150 - 註冊 OP 會員

M0151 - 取得 OP 登入連結

ICP 外國人註冊 API 執行順序
此流程被拆分為兩個階段，由不同的腳本執行。

第一階段: part1_register.py
M0003_01 - 設定註冊資訊

M0007 - 發送簡訊驗證碼

M0010 - 驗證簡訊

M0120 - 外國人身分驗證

M0012 - 變更交易密碼

第二階段: part2_continue_flow.py
M0149 - 檢查是否為 OP 會員

M0150 - 註冊 OP 會員