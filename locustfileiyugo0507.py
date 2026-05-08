import requests
import json
import base64
import os
import re
import time
import random
from datetime import datetime
from locust import HttpUser, task, between
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# --- 1. 加密輔助類別 ---
class CryptoHelper:
    def __init__(self):
        self._rsa_private_key = None
        self._rsa_public_key = None

    def import_rsa_public(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._rsa_public_key = RSA.import_key(pem_key)

    def import_rsa_private(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PRIVATE KEY-----\n{pem_key}\n-----END PRIVATE KEY-----"
        self._rsa_private_key = RSA.import_key(pem_key)

    def sign_sha256(self, data, private_key=None):
        target_key = self._rsa_private_key
        if private_key:
            target_key = RSA.import_key(private_key)
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(target_key).sign(h)
        return base64.b64encode(signature).decode('utf-8')

    @staticmethod
    def aes_encrypt(data, key, iv):
        cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
        padded = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded)).decode('utf-8')

    @staticmethod
    def aes_decrypt(enc_data, key, iv):
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
            decrypted = unpad(cipher.decrypt(base64.b64decode(enc_data)), AES.block_size, style='pkcs7')
            text = decrypted.decode('utf-8')
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return match.group() if match else text
        except:
            return None


# --- 2. Locust 壓力測試主類別 ---
class IcashPayStressUser(HttpUser):
    wait_time = between(1, 2)
    host = "https://icp-payment-stage.icashpay.com.tw"

    def on_start(self):
        self.crypto = CryptoHelper()
        self.account_file = r"C:\icppython\account.txt"
        self.merchant_private_key = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""

        self.user_base_list = []
        if os.path.exists(self.account_file):
            with open(self.account_file, 'r', encoding='utf-8') as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
                for line in lines[1:]:
                    parts = line.split(',')
                    if len(parts) >= 5:
                        self.user_base_list.append({"PayID": parts[4]})

    def _get_timestamp(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    @task
    def icash_pay_dynamic_flow(self):
        if not self.user_base_list: return
        user = random.choice(self.user_base_list)

        # 步驟 10
        new_trade_token = self.run_create_trade()

        # 步驟 11
        if new_trade_token:
            self.run_do_qr_payment(user["PayID"], new_trade_token)

    def run_create_trade(self):
        m_aes_key = "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh"
        m_aes_iv = "KJUYfTyo7Emy2sT9"

        trade_no = f"ITG{datetime.now().strftime('%m%d%H%M%S%f')}"[:20]

        # --- 修改重點：修正 ItemNo 格式 ---
        qr_payload = {
            "PlatformID": "10000236",
            "MerchantID": "10000236",
            "MerchantTradeNo": trade_no,
            "StoreID": "Locust-Stress",
            "StoreName": "壓力測試商店",
            "TradeMode": "2",
            "MerchantTradeDate": self._get_timestamp(),
            "TotalAmount": "500",
            "ItemAmt": "300",
            "UtilityAmt": "200",
            "ItemNonRedeemAmt": "100",
            "UtilityNonRedeemAmt": "100",
            "NonPointAmt": "0",
            "CallbackURL": "https://www.google.com",
            "RedirectURL": "https://www.google.com",
            # 將 ItemNo 改為較長且標準的數字字串 (例如 13 位 EAN 碼格式或 8 位代碼)
            "Item": [{"ItemNo": "001", "ItemName": "壓測商品", "Quantity": "1"}],
        }

        enc_req = self.crypto.aes_encrypt(json.dumps(qr_payload, ensure_ascii=False), m_aes_key, m_aes_iv)
        sig = self.crypto.sign_sha256(enc_req, self.merchant_private_key)
        headers = {'X-iCP-EncKeyID': '289774', 'X-iCP-Signature': sig}

        with self.client.post("/api/V2/Payment/Cashier/CreateTradeICPO",
                              data={'EncData': enc_req},
                              headers=headers,
                              name="10_CreateTrade",
                              catch_response=True) as response:
            try:
                res_obj = response.json()

                if res_obj.get("RtnCode") != 1:
                    response.failure(f"API錯誤: {res_obj.get('RtnCode')} - {res_obj.get('RtnMsg')}")
                    return None

                enc_res_str = res_obj.get("EncData")
                if enc_res_str:
                    decrypted_text = self.crypto.aes_decrypt(enc_res_str, m_aes_key, m_aes_iv)
                    if decrypted_text:
                        inner_data = json.loads(decrypted_text)
                        token = inner_data.get("TradeToken")
                        if token:
                            response.success()
                            return token

                response.failure("解密後未找到 TradeToken")
                return None
            except Exception as e:
                response.failure(f"CreateTrade 解析異常: {str(e)}")
                return None

    def run_do_qr_payment(self, pay_id, trade_token):
        pay_payload = {
            "Timestamp": self._get_timestamp(),
            "PayID": pay_id,
            "TradeToken": trade_token
        }
        with self.client.post("/app/Payment/DoQRPayment",
                              json=pay_payload,
                              name="11_DoQRPayment",
                              catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"支付失敗 HTTP: {response.status_code}")