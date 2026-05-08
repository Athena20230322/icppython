import os
import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 忽略 InsecureRequestWarning 警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# --- 檔案路徑設定 ---
postData_file = r"C:\icppython\OpostData\postData3.txt"
test_data_file = r"C:\icppython\OTestData\ICPAPI\P0002_GetMemberPaymentInfo_1.txt"
enc_output_file = r"c:\enc\Lenc.txt"
SESSION_FILE = r"C:\icppython\session_cache.json"  # 讀取 M0005 產生的 Session

try:
    # --- 1. 讀取 Session 取得 Token ---
    access_token = None
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, 'r') as f:
            session_data = json.load(f)
            access_token = session_data.get("token")

    # --- 2. 讀取 PostData ---
    if not os.path.exists(postData_file):
        raise FileNotFoundError(f"找不到 PostData 檔案: {postData_file}")

    with open(postData_file, 'r') as f:
        file_contents = f.read().strip().split(',')
        if len(file_contents) < 3:
            raise ValueError("postData 檔案格式不正確，應包含至少三個由逗號分隔的值。")
        enc_key_id, signature, enc_data = file_contents

    # --- 3. API 請求設定 ---
    url = 'https://icp-payment-preprod.icashpay.com.tw/app/Payment/GetMemberPaymentInfo'

    # 關鍵修正：Header 必須包含 AccessToken
    headers = {
        'X-iCP-EncKeyID': str(enc_key_id),
        'X-iCP-Signature': signature
    }

    if access_token:
        headers['X-iCP-AccessToken'] = access_token
        # print(f"已帶入 AccessToken: {access_token[:10]}...")
    else:
        print("警告：未找到 AccessToken，API 可能會回傳 1008")

    data = {'EncData': enc_data}

    # --- 4. 發送請求 ---
    response = requests.post(url, headers=headers, data=data, verify=False)
    response.raise_for_status()

    # --- 5. 解析回應 ---
    response_json = response.json()
    rtn_code = response_json.get('RtnCode')
    rtn_msg = response_json.get('RtnMsg', 'N/A')
    enc_text = response_json.get('EncData', '')

    print(f"RtnCode: {rtn_code}")
    print(f"RtnMsg: {rtn_msg}")

    # 將加密資料寫入檔案 (供解密工具使用)
    os.makedirs(os.path.dirname(enc_output_file), exist_ok=True)
    with open(enc_output_file, 'w') as f:
        f.write(enc_text if isinstance(enc_text, str) else json.dumps(enc_text))

    # --- 6. 驗證測試結果 ---
    if os.path.exists(test_data_file):
        with open(test_data_file, 'r') as f:
            test_content = f.read()
            expected_rtn_code = test_content.strip().split(',')[1]

        if str(expected_rtn_code) == str(rtn_code):
            print("Test Passed")
        else:
            print(f"Test Failed. Expected RtnCode: {expected_rtn_code}. Actual RtnCode: {rtn_code}. RtnMsg: {rtn_msg}")
    else:
        print(f"警告：找不到測試資料檔案 {test_data_file}，跳過驗證")

# --- 錯誤處理機制 ---
except FileNotFoundError as e:
    print(f"Test Failed: 找不到檔案 - {e}")
except requests.exceptions.RequestException as e:
    print(f"Test Failed: API 請求失敗 - {e}")
except Exception as e:
    print(f"Test Failed: 發生未預期的錯誤 - {e}")