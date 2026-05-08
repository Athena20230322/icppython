import json
import base64
import re
import time
from datetime import datetime
from queue import Queue, Empty

# 壓力測試工具
from locust import HttpUser, task, between, events

# --- 舊版 Locust StopUser 相容性修正 ---
try:
    from locust import StopUser
except ImportError:
    try:
        from locust.exception import StopUser
    except ImportError:
        class StopUser(Exception):
            pass

# 加密庫
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

    def generate_rsa_key(self):
        key = RSA.generate(2048)
        return {
            'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
            'public_key': key.publickey().export_key(format='PEM').decode('utf-8')
        }

    def import_rsa_public(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._rsa_public_key = RSA.import_key(pem_key)

    def import_rsa_private(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PRIVATE KEY-----\n{pem_key}\n-----END PRIVATE KEY-----"
        self._rsa_private_key = RSA.import_key(pem_key)

    def rsa_encrypt_with_public(self, data):
        key_size = self._rsa_public_key.size_in_bytes()
        max_chunk = key_size - 11
        data_bytes = data.encode('utf-8')
        cipher = PKCS1_v1_5.new(self._rsa_public_key)
        chunks = [cipher.encrypt(data_bytes[i:i + max_chunk]) for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join(chunks)).decode('utf-8')

    def rsa_decrypt_with_private(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size = self._rsa_private_key.size_in_bytes()
        cipher = PKCS1_v1_5.new(self._rsa_private_key)
        decrypted_chunks = [cipher.decrypt(encrypted_bytes[i:i + key_size], b'error_sentinel')
                            for i in range(0, len(encrypted_bytes), key_size)]
        return b''.join(decrypted_chunks).decode('utf-8')

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


# --- 2. 帳號載入 ---
user_data_queue = Queue()
ACCOUNT_FILE = r"C:\icppython\account.txt"


def load_accounts():
    try:
        with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            for line in lines[1:]:
                parts = line.split(',')
                if len(parts) >= 2:
                    user_data_queue.put({"user_code": parts[0], "phone": parts[1]})
        print(f"[*] 帳號載入完畢，共 {user_data_queue.qsize()} 筆。")
    except Exception as e:
        print(f"[!] 讀檔錯誤: {e}")


load_accounts()


# --- 3. Locust 壓力測試類別 ---
class IcashPayStressUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://icp-member-stage.icashpay.com.tw"
    payment_base = "https://icp-payment-stage.icashpay.com.tw"

    def on_start(self):
        self.crypto = CryptoHelper()
        self.aes_info = {}
        self.pay_id = None
        self.current_user = None
        self.merchant_private_key = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""
        try:
            self.current_user = user_data_queue.get_nowait()
        except Empty:
            raise StopUser()

        try:
            self.perform_handshake()
            self.perform_login()
        except Exception as e:
            print(f"[!] 初始化失敗: {e}")
            raise StopUser()

    def perform_handshake(self):
        resp = self.client.post("/api/member/Certificate/GetDefaultPucCert", name="01_GetDefaultCert").json()
        kp = self.crypto.generate_rsa_key()
        self.crypto.import_rsa_private(kp['private_key'])
        self.crypto.import_rsa_public(resp['DefaultPubCert'])
        payload = {'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._ts()}
        enc_data = self.crypto.rsa_encrypt_with_public(json.dumps(payload))
        sig = self.crypto.sign_sha256(enc_data)
        r2 = self.client.post("/api/member/Certificate/ExchangePucCert", data={'EncData': enc_data},
                              headers={'X-iCP-DefaultPubCertID': str(resp['DefaultPubCertID']), 'X-iCP-Signature': sig},
                              name="02_ExchangeCert").json()
        exch_res = json.loads(self.crypto.rsa_decrypt_with_private(r2['EncData']))
        self.crypto.import_rsa_public(exch_res['ServerPubCert'])
        enc_aes_req = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._ts()}))
        sig_aes = self.crypto.sign_sha256(enc_aes_req)
        r3 = self.client.post("/api/member/Certificate/GenerateAES", data={'EncData': enc_aes_req},
                              headers={'X-iCP-ServerPubCertID': str(exch_res['ServerPubCertID']),
                                       'X-iCP-Signature': sig_aes}, name="03_GenAES").json()
        res_aes = json.loads(self.crypto.rsa_decrypt_with_private(r3['EncData']))
        self.aes_info = {'id': res_aes['EncKeyID'], 'key': res_aes['AES_Key'], 'iv': res_aes['AES_IV']}

    def perform_login(self):
        phone = self.current_user['phone']
        res_t = self._call_api(self.host, "/app/MemberInfo/RefreshLoginToken",
                               {"Timestamp": self._ts(), "CellPhone": phone}, name="04_RefreshToken")
        login_token = res_t.get("EncData", {}).get("LoginTokenID", "").split(',')[0]
        res_s = self._call_api(self.host, "/app/MemberInfo/SendAuthSMS",
                               {"Timestamp": self._ts(), "CellPhone": phone, "SMSAuthType": 5,
                                "LoginTokenID": login_token}, name="05_SendSMS")
        auth_code = res_s.get("EncData", {}).get("AuthCode", "")
        self._call_api(self.host, "/app/MemberInfo/UserCodeLogin2022",
                       {"Timestamp": self._ts(), "LoginType": "1", "UserCode": self.current_user['user_code'],
                        "UserPwd": "Aa123456", "SMSAuthCode": auth_code}, name="06_UserLogin")
        res_p = self._call_api(self.payment_base, "/app/Payment/GetMemberPaymentInfo",
                               {"Timestamp": self._ts(), "IsAutoPay": "false", "MerchantID": ""}, name="07_GetPayID")
        p_data = res_p.get("EncData", {})
        for key in ["IcashpayList", "AllIcashpayList", "PaymentList"]:
            target = p_data.get(key)
            if isinstance(target, list) and len(target) > 0:
                self.pay_id = target[0].get("PayID")
                break
            elif isinstance(target, dict):
                self.pay_id = target.get("PayID")
                break

    @task
    def payment_stress_test(self):
        if not self.pay_id: return
        trade_no = f"LT{datetime.now().strftime('%H%M%S%f')}"[:20]
        qr_payload = {
            "PlatformID": "10000236", "MerchantID": "10000236", "MerchantTradeNo": trade_no,
            "StoreID": "Locust-Test", "StoreName": "Locust-Test", "TradeMode": "2",
            "MerchantTradeDate": self._ts(), "TotalAmount": "500", "ItemAmt": "300",
            "UtilityAmt": "200", "ItemNonRedeemAmt": "100", "UtilityNonRedeemAmt": "100",
            "NonPointAmt": "0", "CallbackURL": "https://www.google.com",
            "RedirectURL": "https://www.google.com", "AuthICPAccount": "",
            "Item": [{"ItemNo": "001", "ItemName": "壓測商品", "Quantity": "1"}],
        }
        res_qr = self._call_api(self.payment_base, "/api/V2/Payment/Cashier/CreateTradeICPO", qr_payload,
                                is_merchant=True, name="10_CreateTrade")
        trade_token = res_qr.get("EncData", {}).get("TradeToken") if isinstance(res_qr.get("EncData"), dict) else None
        if trade_token:
            pay_payload = {"Amount": "5", "MerchantID": "10000236", "MerchantTradeNo": trade_no,
                           "PayID": str(self.pay_id), "TradeToken": trade_token}
            self._call_api(self.payment_base, "/app/Payment/DoQRPayment", pay_payload, name="11_DoQRPayment")

    def _ts(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def _call_api(self, base_url, action, payload, is_merchant=False, name=None):
        if is_merchant:
            k, iv = "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh", "KJUYfTyo7Emy2sT9"
            enc = self.crypto.aes_encrypt(json.dumps(payload), k, iv)
            sig = self.crypto.sign_sha256(enc, self.merchant_private_key)
            headers = {'X-iCP-EncKeyID': '289774', 'X-iCP-Signature': sig}
        else:
            enc = self.crypto.aes_encrypt(json.dumps(payload), self.aes_info['key'], self.aes_info['iv'])
            sig = self.crypto.sign_sha256(enc)
            headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}

        target_url = f"{base_url.rstrip('/')}/{action.lstrip('/')}"

        with self.client.post(target_url, data={'EncData': enc}, headers=headers, name=name or action,
                              catch_response=True) as resp:
            try:
                res_j = resp.json()
                if "EncData" in res_j and isinstance(res_j['EncData'], str):
                    use_k = k if is_merchant else self.aes_info['key']
                    use_iv = iv if is_merchant else self.aes_info['iv']
                    dec = self.crypto.aes_decrypt(res_j['EncData'], use_k, use_iv)
                    if dec:
                        try:
                            res_j['EncData'] = json.loads(dec)
                        except:
                            res_j['EncData'] = dec

                # --- 修改後的錯誤監控邏輯 ---
                if res_j.get("RtnCode") != 1 and res_j.get("Status") != "Success":
                    error_msg = f"業務失敗! RtnCode: {res_j.get('RtnCode')}, Msg: {res_j.get('RtnMsg') or res_j.get('Message')}"
                    # 1. 輸出到終端機
                    print(f"\n[!] 請求失敗 ({name}): {error_msg}")
                    print(f"    原始回應: {json.dumps(res_j, ensure_ascii=False)}")
                    # 2. 標記為 Fail 並顯示在 Locust UI
                    resp.failure(error_msg)

                return res_j
            except Exception as e:
                resp.failure(f"系統錯誤: {e}")
                return {}