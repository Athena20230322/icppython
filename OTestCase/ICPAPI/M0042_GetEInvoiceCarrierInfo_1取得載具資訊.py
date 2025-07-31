import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 忽略 InsecureRequestWarning 警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 檔案路徑設定 ---
# 將路徑指向 P0010 對應的 postData 和測試資料檔案
postData_file = "C:\\icppython\\OpostData\\postData4.txt"
test_data_file = "C:\\icppython\\OTestData\\ICPAPI\\M0042_GetEInvoiceCarrierInfo_1.txt"
enc_output_file = "c:\\enc\\Lenc.txt"

try:
    # --- 讀取 PostData ---
    with open(postData_file, 'r') as f:
        file_contents = f.read().strip().split(',')
        if len(file_contents) < 3:
            raise ValueError("postData 檔案格式不正確，應包含至少三個由逗號分隔的值。")
        enc_key_id, signature, enc_data = file_contents

    # --- API 請求設定 ---
    # 更新為 P0010 對應的 API URL
    url = 'https://icp-member-stage.icashpay.com.tw/app/MemberInfo/GetEInvoiceCarrierInfo'
    headers = {
        'X-ICP-EncKeyID': enc_key_id,
        'X-iCP-Signature': signature
    }
    data = {'EncData': enc_data}

    # --- 發送請求 ---
    response = requests.post(url, headers=headers, data=data, verify=False)
    response.raise_for_status()  # 如果 HTTP 狀態碼不是 2xx，則拋出異常

    # --- 解析回應 (採用 P0018 的安全作法) ---
    response_json = response.json()
    rtn_code = response_json.get('RtnCode')
    rtn_msg = response_json.get('RtnMsg', 'N/A')  # 如果沒有 RtnMsg，預設為 N/A
    enc_text = response_json.get('EncData', '')

    # --- 輸出回應內容 (與 P0018 格式一致) ---
    print(f"RtnCode: {rtn_code}")
    print(f"RtnMsg: {rtn_msg}")

    # 將加密資料寫入檔案
    with open(enc_output_file, 'w') as f:
        f.write(enc_text)

    # --- 驗證測試結果 (採用 P0018 的邏輯) ---
    with open(test_data_file, 'r') as f:
        file_contents = f.read()
        expected_rtn_code = file_contents.strip().split(',')[1]

    # 比較期望的 RtnCode 與實際的 RtnCode
    if expected_rtn_code == str(rtn_code):
        # 如果兩者相等，印出 "Test Passed"
        print("Test Passed")
    else:
        # 如果不相等，印出包含 RtnMsg 的詳細失敗訊息
        print(f"Test Failed. Expected RtnCode: {expected_rtn_code}. Actual RtnCode: {rtn_code}. RtnMsg: {rtn_msg}")

# --- 完整的錯誤處理機制 (從 P0018 移植) ---
except FileNotFoundError as e:
    print(f"Test Failed: 找不到檔案 - {e}")
except requests.exceptions.RequestException as e:
    print(f"Test Failed: API 請求失敗 - {e}")
except Exception as e:
    print(f"Test Failed: 發生未預期的錯誤 - {e}")
