# icppython

本專案為 iCash Pay (ICP) 相關 API 的 Python 自動化測試腳本。

---

## 🚀 主要功能腳本

| 腳本檔案                           | 功能說明                                                                                 |
|------------------------------------|------------------------------------------------------------------------------------------|
| `run_icplogin.py`                  | 執行登入流程，並在完成後產出 API 測試報告。                                              |
| `run_icpaccountclose.py`           | 執行結清帳號流程，執行後將直接結清指定帳號。                                              |
| `full_registration_flow.py`        | (SIT/UAT) 一鍵註冊本國人會員完整流程。                                                    |
| `full_registration_flowUAT`        | (SIT/UAT) 一鍵註冊本國人會員完整流程。                                                    |
| `master_nextstep_runner.py`        | 註冊後 NextStep 狀態流程，支援 Next1, Next2, Next4, Next5, Next6, Next9, Next13。         |
| `run_logincarrefourpay.py`         | 家樂福登入付款 UAT 純金。                                                                |
| `run_logincarrefourpaycashandop.py`| 家樂福登入付款 UAT 點+金。                                                               |
| `run_logincarrefourpayonlyop.py`   | 家樂福登入付款 UAT 純點。                                                                |
| `run_login711paycashandOP.py`      | 超商 SIT 剩餘點+金。                                                                     |
| `Integrated_QA_Tool_GetTopUpBarCode.py` | 產出條碼並執行現金儲值。                                                            |
| `Integrated_QA_Tool_iyugo.py`      | 產資料，使用 `accountonly.txt`。                                                         |
| `locust_iyugo_final.py`            | 使用 `account+iyugo.txt` 進行壓力測試。                                                  |

---

## 📁 目錄說明

- `icploginapireport/`：存放 `run_icplogin.py` 產生的 HTML 測試報告。

---

## 📋 API 執行流程

### ICP 本國人註冊 API 執行順序
由 `full_registration_flow.py` 完整執行：

1. M0003_01 - 設定註冊資訊
2. M0007    - 發送簡訊驗證碼
3. M0010    - 驗證簡訊
4. M0004    - 身分驗證
5. M0012    - 變更交易密碼
6. M0149    - 檢查是否為 OP 會員
7. M0150    - 註冊 OP 會員
8. M0151    - 取得 OP 登入連結

### ICP 外國人註冊 API 執行順序

**第一階段：** `part1_register.py`
- M0003_01 - 設定註冊資訊
- M0007    - 發送簡訊驗證碼
- M0010    - 驗證簡訊
- M0120    - 外國人身分驗證
- M0012    - 變更交易密碼

**第二階段：** `part2_continue_flow.py`
- M0149    - 檢查是否為 OP 會員
- M0150    - 註冊 OP 會員

---

## 📝 常用檔案與說明

- `C:\icppython\usercode.txt`：UAT 帳號
- `C:\icppython\cellphone.txt`：UAT 電話

---

## 🛠️ 執行範例

```shell
# 產出條碼並執行現金儲值
python Integrated_QA_Tool_GetTopUpBarCode.py