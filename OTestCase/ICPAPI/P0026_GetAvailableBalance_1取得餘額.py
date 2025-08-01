import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 忽略 InsecureRequestWarning 警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 檔案路徑設定 ---
postData_file = "C:\\icppython\\OpostData\\postData7.txt"
test_data_file = "C:\\icppython\\OTestData\\ICPAPI\\P0026_GetAvailableBalance_1.txt"
enc_output_file = "c:\\enc\\Lenc.txt"

try:
    # --- 讀取 PostData ---
    with open(postData_file, 'r') as f:
        file_contents = f.read().strip().split(',')
        if len(file_contents) < 3:
            raise ValueError("postData 檔案格式不正確，應包含至少三個由逗號分隔的值。")
        enc_key_id, signature, enc_data = file_contents

    # --- API 請求設定 ---
    url = 'https://icp-payment-stage.icashpay.com.tw/app/Payment/GetAvailableBalance'
    headers = {
        'X-ICP-EncKeyID': enc_key_id,
        'X-iCP-Signature': signature
    }
    data = {'EncData': enc_data}

    # --- 發送請求 ---
    response = requests.post(url, headers=headers, data=data, verify=False)
    response.raise_for_status()  # 如果 HTTP 狀態碼不是 2xx，則拋出異常

    # --- 解析回應 ---
    response_json = response.json()
    rtn_code = response_json.get('RtnCode')
    rtn_msg = response_json.get('RtnMsg', 'N/A')  # 如果沒有 RtnMsg，預設為 N/A
    enc_text = response_json.get('EncData', '')

    # --- 輸出回應內容 ---
    # 為了讓主程式能解析，我們將 RtnCode 和 RtnMsg 印在同一行
    print(f"RtnCode: {rtn_code}")
    print(f"RtnMsg: {rtn_msg}")

    # 將加密資料寫入檔案
    with open(enc_output_file, 'w') as f:
        f.write(enc_text)

    # --- 驗證測試結果 ---
    with open(test_data_file, 'r') as f:
        file_contents = f.read()
        expected_rtn_code = file_contents.strip().split(',')[1]

    # 【***主要修改處***】
    # 這裡的邏輯是判斷測試是否通過的核心。

    # 1. 比較「期望的 RtnCode」(從測試資料檔讀取) 與「實際的 RtnCode」(從 API 回應獲得)。
    #    使用 str() 是為了確保兩邊的型別一致，避免因型別不同而判斷錯誤。
    if expected_rtn_code == str(rtn_code):
        # 2. 如果兩者相等，表示測試結果符合預期，印出 "Test Passed"。
        #    主執行腳本會根據這個關鍵字來判斷此案例為「成功」。
        print("Test Passed")
    else:
        # 3. 如果兩者不相等，表示測試結果不符合預期，印出 "Test Failed" 關鍵字。
        #    【關鍵修改】：在失敗訊息中，除了顯示期望與實際的 RtnCode 外，
        #    額外加入了從 API 回應中解析出來的「RtnMsg」。
        #    這樣主執行腳本就能捕捉到這個完整的錯誤訊息，並呈現在最終的 HTML 報告中，
        #    讓我們能立即知道失敗的「原因」，而不僅僅是看到一個錯誤的代碼。
        print(f"Test Failed. Expected RtnCode: {expected_rtn_code}. Actual RtnCode: {rtn_code}. RtnMsg: {rtn_msg}")

except FileNotFoundError as e:
    print(f"Test Failed: 找不到檔案 - {e}")
except requests.exceptions.RequestException as e:
    print(f"Test Failed: API 請求失敗 - {e}")
except Exception as e:
    print(f"Test Failed: 發生未預期的錯誤 - {e}")
