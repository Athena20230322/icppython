import json
import base64
import re
import time
from datetime import datetime
from locust import HttpUser, task, between, events
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# --- 1. 加密輔助類別 (沿用原邏輯) ---
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


# --- 2. Locust 壓力測試使用者 ---
class IcashPayUser(HttpUser):
    # 設定請求間隔 (秒)
    wait_time = between(1, 3)

    # 基本設定
    MEMBER_BASE = "https://icp-member-stage.icashpay.com.tw/"
    PAYMENT_BASE = "https://icp-payment-stage.icashpay.com.tw/"

    # 測試用帳號資訊 (壓測時建議隨機或循環使用多組)
    TEST_USER_CODE = "i1777013632"
    TEST_PHONE = "0950001776"

    MERCHANT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""

    def on_start(self):
        """ 每個虛擬使用者啟動時執行的初始化 (Handshake & Login) """
        self.crypto = CryptoHelper()
        self.aes_info = {}
        self.pay_id = None
        self._perform_handshake()
        self._perform_login()
        self._get_pay_id()

    def _get_ts(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def _perform_handshake(self):
        # 取得預設憑證
        resp = self.client.post(f"{self.MEMBER_BASE}api/member/Certificate/GetDefaultPucCert").json()
        kp = self.crypto.generate_rsa_key()
        self.crypto.import_rsa_private(kp['private_key'])
        self.crypto.import_rsa_public(resp['DefaultPubCert'])

        # 交換憑證
        payload = {'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._get_ts()}
        enc_data = self.crypto.rsa_encrypt_with_public(json.dumps(payload, ensure_ascii=False))
        sig = self.crypto.sign_sha256(enc_data)

        resp_exch = self.client.post(f"{self.MEMBER_BASE}api/member/Certificate/ExchangePucCert",
                                     data={'EncData': enc_data},
                                     headers={'X-iCP-DefaultPubCertID': str(resp['DefaultPubCertID']),
                                              'X-iCP-Signature': sig}).json()

        exch_res = json.loads(self.crypto.rsa_decrypt_with_private(resp_exch['EncData']))
        self.crypto.import_rsa_public(exch_res['ServerPubCert'])

        # 產生 AES
        enc_data_aes = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._get_ts()}))
        sig_aes = self.crypto.sign_sha256(enc_data_aes)
        resp_aes = self.client.post(f"{self.MEMBER_BASE}api/member/Certificate/GenerateAES",
                                    data={'EncData': enc_data_aes},
                                    headers={'X-iCP-ServerPubCertID': str(exch_res['ServerPubCertID']),
                                             'X-iCP-Signature': sig_aes}).json()

        res = json.loads(self.crypto.rsa_decrypt_with_private(resp_aes['EncData']))
        self.aes_info = {'id': res['EncKeyID'], 'key': res['AES_Key'], 'iv': res['AES_IV']}

    def _call_icp_api(self, url, payload, is_merchant=False):
        """ 通用加密 API 呼叫封裝 """
        if is_merchant:
            m_key, m_iv = "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh", "KJUYfTyo7Emy2sT9"
            enc = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), m_key, m_iv)
            sig = self.crypto.sign_sha256(enc, self.MERCHANT_PRIVATE_KEY)
            headers = {'X-iCP-EncKeyID': '289774', 'X-iCP-Signature': sig}
            use_key, use_iv = m_key, m_iv
        else:
            enc = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                          self.aes_info['iv'])
            sig = self.crypto.sign_sha256(enc)
            headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}
            use_key, use_iv = self.aes_info['key'], self.aes_info['iv']

        with self.client.post(url, data={'EncData': enc}, headers=headers, catch_response=True) as response:
            try:
                res_json = response.json()
                if "EncData" in res_json:
                    dec = self.crypto.aes_decrypt(res_json['EncData'], use_key, use_iv)
                    res_json['EncData'] = json.loads(dec) if dec else None
                return res_json
            except:
                response.failure("JSON Parsing Error")
                return {}

    def _perform_login(self):
        # Refresh Token
        res = self._call_icp_api(f"{self.MEMBER_BASE}app/MemberInfo/RefreshLoginToken",
                                 {"Timestamp": self._get_ts(), "CellPhone": self.TEST_PHONE})
        token = res.get("EncData", {}).get("LoginTokenID", "").split(',')[0]

        # SMS Auth
        res_sms = self._call_icp_api(f"{self.MEMBER_BASE}app/MemberInfo/SendAuthSMS",
                                     {"Timestamp": self._get_ts(), "CellPhone": self.TEST_PHONE, "SMSAuthType": 5,
                                      "LoginTokenID": token})
        auth_code = res_sms.get("EncData", {}).get("AuthCode", "")

        # Login
        self._call_icp_api(f"{self.MEMBER_BASE}app/MemberInfo/UserCodeLogin2022",
                           {"Timestamp": self._get_ts(), "LoginType": "1", "UserCode": self.TEST_USER_CODE,
                            "UserPwd": "Aa123456", "SMSAuthCode": auth_code})

    def _get_pay_id(self):
        res_pay = self._call_icp_api(f"{self.MEMBER_BASE}app/Payment/GetMemberPaymentInfo",
                                     {"Timestamp": self._get_ts(), "IsAutoPay": "false", "MerchantID": ""})
        p_data = res_pay.get("EncData", {})
        for key in ["IcashpayList", "AllIcashpayList", "PaymentList"]:
            target = p_data.get(key)
            if isinstance(target, dict):
                self.pay_id = target.get("PayID")
            elif isinstance(target, list) and len(target) > 0:
                self.pay_id = target[0].get("PayID")
            if self.pay_id: break

    # --- 重點：壓測 Task ---
    @task
    def test_full_payment_flow(self):
        """ 模擬 建立交易 -> 確認支付 的完整循環 """
        trade_no = f"LT{datetime.now().strftime('%m%d%H%M%S%f')}"[:20]

        # 1. CreateTradeICPO (Merchant API)
        qr_payload = {
            "PlatformID": "10000236", "MerchantID": "10000236", "MerchantTradeNo": trade_no,
            "StoreID": "Locust-Test", "StoreName": "Locust-Test", "TradeMode": "2",
            "MerchantTradeDate": self._get_ts(), "TotalAmount": "500", "ItemAmt": "300",
            "UtilityAmt": "200", "ItemNonRedeemAmt": "100", "UtilityNonRedeemAmt": "100",
            "NonPointAmt": "0", "CallbackURL": "https://www.google.com", "RedirectURL": "https://www.google.com",
            "AuthICPAccount": "", "Item": [{"ItemNo": "001", "ItemName": "壓測商品", "Quantity": "1"}]
        }

        res_qr = self._call_icp_api(f"{self.PAYMENT_BASE}api/V2/Payment/Cashier/CreateTradeICPO", qr_payload,
                                    is_merchant=True)

        if res_qr.get("RtnCode") == 1:
            # 2. DoQRPayment (App API)
            pay_payload = {
                "Amount": "5",
                "MerchantID": "10000236",
                "MerchantTradeNo": trade_no,
                "Mission": "",
                "PayID": str(self.pay_id),
                "StoreID": "", "StoreName": "", "Team_number": ""
            }
            res_pay = self._call_icp_api(f"{self.PAYMENT_BASE}app/Payment/DoQRPayment", pay_payload)

            if res_pay.get("RtnCode") != 1:
                print(f"Payment Failed: {res_pay.get('RtnMsg')}")
        else:
            print(f"Create Trade Failed: {res_qr.get('RtnMsg')}")