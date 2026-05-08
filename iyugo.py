import json
import base64
import time
import requests
import qrcode
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# --- 工具函式：取得當前時間與交易編號 ---
def get_current_time():
    now = datetime.now()
    trade_no = f"Sample{now.strftime('%Y%m%d%H%M%S')}"
    trade_date = now.strftime('%Y/%m/%d %H:%M:%S')
    return trade_no, trade_date

# --- AES 加解密類別 (AES-256-CBC) ---
class AESCipher:
    def __init__(self, key, iv):
        self.key = key.encode('utf-8')
        self.iv = iv.encode('utf-8')

    def encrypt(self, raw_text):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        # PKCS7 Padding
        padded_data = pad(raw_text.encode('utf-8'), AES.block_size)
        encrypted = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, enc_text):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        enc_data = base64.b64decode(enc_text)
        decrypted = unpad(cipher.decrypt(enc_data), AES.block_size)
        return decrypted.decode('utf-8')

# --- RSA 簽名函式 ---
def sign_data(data_to_sign, private_key_pem):
    key = RSA.import_key(private_key_pem)
    h = SHA256.new(data_to_sign.encode('utf-8'))
    signature = pkcs1_15.new(key).sign(h)
    return base64.b64encode(signature).decode('utf-8')

# --- 設定參數 ---
AES_KEY = "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh"
AES_IV = "KJUYfTyo7Emy2sT9"
CLIENT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""

# 1. 準備數據
trade_no, trade_date = get_current_time()
data = {
    "PlatformID": "10000236",
    "MerchantID": "10000236",
    "MerchantTradeNo": trade_no,
    "StoreID": "Dev2-Test",
    "StoreName": "Dev2-Test",
    "TradeMode": "2",
    "MerchantTradeDate": trade_date,
    "TotalAmount": "500",
    "ItemAmt": "300",
    "UtilityAmt": "200",
    "ItemNonRedeemAmt": "100",
    "UtilityNonRedeemAmt": "100",
    "NonPointAmt": "0",
    "CallbackURL": "https://www.google.com?CallbackURL",
    "RedirectURL": "https://www.google.com?RedirectURL",
    "AuthICPAccount": "",
    "Item": [{"ItemNo": "001", "ItemName": "測試商品1", "Quantity": "1"}],
}

# 2. 加密與簽章
cipher = AESCipher(AES_KEY, AES_IV)
enc_data = cipher.encrypt(json.dumps(data, ensure_ascii=False))
x_icp_signature = sign_data(enc_data, CLIENT_PRIVATE_KEY)

print(f"Encrypted Data (EncData): {enc_data}")
print(f"X-iCP-Signature: {x_icp_signature}")

# 3. 發送 POST 請求
api_url = "https://icp-payment-stage.icashpay.com.tw/api/V2/Payment/Cashier/CreateTradeICPO"
headers = {
    'X-iCP-EncKeyID': '289774',
    'X-iCP-Signature': x_icp_signature,
    'Content-Type': 'application/x-www-form-urlencoded',
}
payload = {'EncData': enc_data}

try:
    response = requests.post(api_url, headers=headers, data=payload)
    response_text = response.text
    print(f"Response: {response_text}")

    # 4. 解析回應
    resp_json = response.json()
    if "EncData" in resp_json:
        decrypted_resp = cipher.decrypt(resp_json["EncData"])
        print(f"Decrypted Response Data: {decrypted_resp}")

        parsed_resp = json.loads(decrypted_resp)
        trade_token = parsed_resp.get("TradeToken")

        if trade_token:
            print(f"Trade Token: {trade_token}")

            # 在終端機顯示 QR Code (類似 qrcode-terminal)
            qr_console = qrcode.QRCode()
            qr_console.add_data(trade_token)
            qr_console.print_ascii(invert=True)

            # 儲存成圖片檔案
            img = qrcode.make(trade_token)
            img.save("grab.png")
            print("QR Code saved as grab.png")

except Exception as e:
    print(f"Failed to process request: {e}")

# 5. 儲存 MerchantTradeNo 到檔案
file_name = 'iyugoMerchantTradeNo.txt'
with open(file_name, 'w', encoding='utf-8') as f:
    f.write(f"MerchantTradeNo: {trade_no}")
print(f"MerchantTradeNo 已儲存到 {file_name}")