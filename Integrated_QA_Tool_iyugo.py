import requests
import json
import base64
import os
import re
import time
import random
from datetime import datetime
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


# --- 2. API 客戶端 ---
class IcashPayClient:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.payment_url = "https://icp-payment-stage.icashpay.com.tw/"
        self.crypto = CryptoHelper()
        self.session = requests.Session()
        self.aes_info = {}
        self.merchant_private_key = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""

    def _get_timestamp(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def handshake(self):
        resp = self.session.post(f"{self.member_url}api/member/Certificate/GetDefaultPucCert").json()
        kp = self.crypto.generate_rsa_key()
        self.crypto.import_rsa_private(kp['private_key'])
        self.crypto.import_rsa_public(resp['DefaultPubCert'])
        payload = {'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._get_timestamp()}
        enc_data = self.crypto.rsa_encrypt_with_public(json.dumps(payload, ensure_ascii=False))
        sig = self.crypto.sign_sha256(enc_data)
        resp_exch = self.session.post(f"{self.member_url}api/member/Certificate/ExchangePucCert",
                                      data={'EncData': enc_data},
                                      headers={'X-iCP-DefaultPubCertID': str(resp['DefaultPubCertID']),
                                               'X-iCP-Signature': sig}).json()
        exch_res = json.loads(self.crypto.rsa_decrypt_with_private(resp_exch['EncData']))
        self.crypto.import_rsa_public(exch_res['ServerPubCert'])
        enc_data_aes = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._get_timestamp()}))
        sig_aes = self.crypto.sign_sha256(enc_data_aes)
        resp_aes = self.session.post(f"{self.member_url}api/member/Certificate/GenerateAES",
                                     data={'EncData': enc_data_aes},
                                     headers={'X-iCP-ServerPubCertID': str(exch_res['ServerPubCertID']),
                                              'X-iCP-Signature': sig_aes}).json()
        res = json.loads(self.crypto.rsa_decrypt_with_private(resp_aes['EncData']))
        self.aes_info = {'id': res['EncKeyID'], 'key': res['AES_Key'], 'iv': res['AES_IV']}

    def call_api(self, base_url, action, payload, is_merchant_api=False):
        if is_merchant_api:
            m_aes_key = "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh"
            m_aes_iv = "KJUYfTyo7Emy2sT9"
            enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), m_aes_key, m_aes_iv)
            sig = self.crypto.sign_sha256(enc_data, self.merchant_private_key)
            headers = {'X-iCP-EncKeyID': '289774', 'X-iCP-Signature': sig}
            use_key, use_iv = m_aes_key, m_aes_iv
        else:
            enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                               self.aes_info['iv'])
            sig = self.crypto.sign_sha256(enc_data)
            headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}
            use_key, use_iv = self.aes_info['key'], self.aes_info['iv']

        try:
            r = self.session.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers)
            resp = r.json()
            if "EncData" in resp and isinstance(resp['EncData'], str):
                decrypted = self.crypto.aes_decrypt(resp['EncData'], use_key, use_iv)
                if decrypted:
                    try:
                        resp['EncData'] = json.loads(decrypted)
                    except:
                        resp['EncData'] = decrypted
            return resp
        except Exception as e:
            return {"Status": "Error", "Message": str(e)}


# --- 3. 處理邏輯 ---
def process_iyugo_barcode_generation():
    ACCOUNT_FILE = r"C:\icppython\account.txt"
    print(f"[*] 啟動測試開發工具：產出 iyugo 正掃支付 Token 資料...")

    if not os.path.exists(ACCOUNT_FILE):
        print(f"[!] 錯誤: 找不到檔案 {ACCOUNT_FILE}")
        return

    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    client = IcashPayClient()
    final_output_rows = []
    header_str = "UserCode,CellPhone,LoginTokenID,authcode,PayID,TradeToken,MerchantTradeNo"

    for idx, line in enumerate(lines[1:], 1):
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue
        user_code, phone = parts[0], parts[1]
        try:
            count_val = int(parts[5]) if len(parts) > 5 and parts[5] else 1
        except:
            count_val = 1

        print(f"\n>>> [{idx}] 帳號: {phone}")
        try:
            client.handshake()
            # 1~4 登入流程
            res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                        {"Timestamp": client._get_timestamp(), "CellPhone": phone})
            new_token = res_token.get("EncData", {}).get("LoginTokenID", "").split(',')[0] if isinstance(
                res_token.get("EncData"), dict) else ""

            res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                      {"Timestamp": client._get_timestamp(), "CellPhone": phone, "SMSAuthType": 5,
                                       "UserCode": "", "LoginTokenID": new_token})
            new_auth = res_sms.get("EncData", {}).get("AuthCode", "") if isinstance(res_sms.get("EncData"),
                                                                                    dict) else ""

            client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                            {"Timestamp": client._get_timestamp(), "LoginType": "1", "UserCode": user_code,
                             "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

            res_pay = client.call_api(client.payment_url, "app/Payment/GetMemberPaymentInfo",
                                      {"Timestamp": client._get_timestamp(), "IsAutoPay": "false", "MerchantID": ""})
            pay_id = None
            p_data = res_pay.get("EncData", {})
            if isinstance(p_data, dict):
                for key in ["IcashpayList", "AllIcashpayList", "PaymentList"]:
                    target = p_data.get(key)
                    if isinstance(target, dict):
                        pay_id = target.get("PayID")
                    elif isinstance(target, list) and len(target) > 0:
                        pay_id = target[0].get("PayID")
                    if pay_id: break

            # 5. 產出 TradeToken
            for i in range(count_val):
                trade_no = f"ITG{datetime.now().strftime('%m%d%H%M%S%f')}"[:20]

                # --- 修改點：優化商店名稱與參數 ---
                qr_payload = {
                    "PlatformID": "10000236",
                    "MerchantID": "10000236",
                    "MerchantTradeNo": trade_no,
                    "StoreID": "Dev2-Test",
                    "StoreName": "Dev2-Test",
                    "TradeMode": "2",
                    "MerchantTradeDate": client._get_timestamp(),
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

                res_qr = client.call_api(client.payment_url, "api/V2/Payment/Cashier/CreateTradeICPO", qr_payload,
                                         is_merchant_api=True)

                trade_token = ""
                if isinstance(res_qr.get("EncData"), dict):
                    trade_token = res_qr["EncData"].get("TradeToken", "")

                if trade_token:
                    print(f"    └─ [{i + 1}] 成功! Token: {trade_token[:10]}...")
                else:
                    print(f"    └─ [{i + 1}] 失敗! RtnCode: {res_qr.get('RtnCode')} | Msg: {res_qr.get('RtnMsg')}")

                final_output_rows.append([user_code, phone, new_token, new_auth, str(pay_id), trade_token, trade_no])
                time.sleep(0.1)
        except Exception as e:
            print(f"❌ 異常: {str(e)}")

    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header_str + "\n")
        for row in final_output_rows: f.write(",".join(row) + "\n")
    print(f"\n[*] 處理完畢。")


if __name__ == '__main__':
    process_iyugo_barcode_generation()