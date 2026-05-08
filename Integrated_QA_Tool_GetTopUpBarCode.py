import requests
import json
import base64
import os
import re
import time
from datetime import datetime
from urllib.parse import quote
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# 設定路徑
ACCOUNT_FILE = "C:\\icppython\\account.txt"
REFUND_FILE = "markettoprefund.txt"

# ----------------------------------------------------------------
# 市場儲值 (SETTopUp) 專用固定參數
# ----------------------------------------------------------------
MARKET_AES_KEY = "VhoGVCInVF2UJ1cQBVZCF48lGUVIoCng"
MARKET_AES_IV = "z3P4Se8qTFE0F1xI"
MARKET_ENC_KEY_ID = "288768"
MARKET_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEA0hXyO7E10c4WR/S1XUFUyvlLS8wX/3RoL9nE4kwWJC+nTy8AFSVBgNz2KPnv3If+q8lG3bqq6TCiBmZxP33hbQH1H/cZPHag644nHlHc0/ZSunXB92jprH4xf96wfev12wqrMbCnYKytInEJnuHN+n3eq0LuyQ/WRcPVROJWxYFUO+uGLbFohtmppb0f/cSKOr0hVP15qZAEVSQwYHhu1CJAI/XoRLkZd87A2KHzvVJ2qkbjRbzXemRToE0v3GrWoUoBIMW3cJxgKieMW/HhQHfnz8njTf4nYlA4OSi2U43OA3Z9T+9gB5I8FvfOokt/LfhvO5q/l7QWB+yaX2hvuQIDAQABAoIBAAd57PYnWws1mpDiej7Ql6AmiYGvyG3YmmmThiBohUQx5vIYMdhOzFs14dO4+0p9k3hRECLNZQ4p4yY3qJGSHP7YWj0SOdVvQlBHrYg0cReg9TY6ARZZJzGyhvfuOJkul7/9C/UXfIlh88JdQ/KhxgcDSjSNi/pfRCiU7MbICD78h/pCS1zIWHaICZ2aL5rV2o5JwCcvDP8p3F+LFW/5u5kK0D0Pd29FXhf5MKHC4Mgrn2I44Uyhdud2Mf7wdvYvvcv2Nzn/EvM7uYZpkEyC3Y1Ow037fZjO3pVCVRt8Mbo4B75ORqXQnr1SbKXWXM/unUEIfMhsBRhx/diDCO8xyiECgYEA8UXIvYWREf+EN5EysmaHcv1jEUgFym8xUiASwwAv+LE9jQJSBiVym13rIGs01k1RN9z3/RVc+0BETTy9qEsUzwX9oTxgqlRk8R3TK7YEg6G/W/7D5DDM9bS/ncU7PlKA/FaEasHCfjs0IY5yJZFYrcA2QvvCl1X1NUZ4Hyumk1ECgYEA3ujTDbDNaSy/++4W/Ljp5pIVmmO27jy30kv1d3fPG6HRtPvbwRyUk/Y9PQpVpd7Sx/+GN+95Z3/zy1IHrbHN5SxE+OGzLrgzgj32EOU+ZJk5uj9qNBkNXh5prcOcjGcMcGL9OAC2oaWaOxrWin3fAzDsCoGrlzSzkVANnBRB6+kCgYEA2EaA0nq3dxW/9HugoVDNHCPNOUGBh1wzLvX3O3ughOKEVTF+S2ooGOOQkGfpXizCoDvgxKnwxnxufXn0XLao+YbaOz0/PZAXSBg/IlCwLTrBqXpvKM8h+yLCHXAeUhhs7UW0v2neqX7ylR32bnyirGW/fj3lyfjQrKf1p6NeV3ECgYB2X+fspk5/Iu+VJxv3+27jLgLg6UE1BPONbx8c4XgPsYB+/xz1UWsppCNjLgDLxCflY7HwNHEhYJakC5zeRcUUhcze6mTQU6uu556r3EGlBKXeXVzV69Pofngaef3Bpdu6NydHvUE/WIUuDBOQmkV7GVjQP4pTEv6lFYEUuMFFOQKBgHfINuaiIlITl/u59LPrvhTZoq6qg7N/3wVeAjYvbpv+b2cFgvOMQAr+S8eCDzijy2z4MENBTr/q6mkKe4NHFGtodP+bjSYEG+GnBEG+EUpAx3Wh/BL2f/sIiSOH9ODB6B847F+apa0OTawmslgGna9/985egGMto9g16EQ4ib1M
-----END PRIVATE KEY-----"""


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

    def sign_sha256(self, data, custom_priv_key=None):
        target_key = custom_priv_key if custom_priv_key else self._rsa_private_key
        if not target_key: raise ValueError("尚未匯入私鑰")
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


class IcashPayClient:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.payment_url = "https://icp-payment-stage.icashpay.com.tw/"
        self.crypto = CryptoHelper()
        self.session = requests.Session()
        self.aes_info = {}

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

    def call_api(self, base_url, action, payload):
        enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                           self.aes_info['iv'])
        sig = self.crypto.sign_sha256(enc_data)
        headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}
        resp = self.session.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers).json()
        if "EncData" in resp and isinstance(resp['EncData'], str):
            decrypted = self.crypto.aes_decrypt(resp['EncData'], self.aes_info['key'], self.aes_info['iv'])
            if decrypted:
                try:
                    resp['EncData'] = json.loads(decrypted)
                except:
                    resp['EncData'] = decrypted
        return resp

    def get_total_coins(self):
        payload = {"Timestamp": self._get_timestamp()}
        resp = self.call_api(self.payment_url, "app/Payment/GetTotalCoins", payload)
        return resp.get("EncData", {})


def process_accounts():
    client = IcashPayClient()
    if not os.path.exists(ACCOUNT_FILE):
        print(f"找不到檔案: {ACCOUNT_FILE}")
        return

    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if not lines: return

    header = "UserCode,CellPhone,LoginTokenID,authcode,Barcode,Count"
    updated_rows = []

    for line in lines[1:]:
        if not line.strip(): continue
        acc = [p.strip() for p in line.split(',')]
        while len(acc) < 6: acc.append("")

        user_code, phone, current_token, current_auth, current_barcode, count_str = acc

        try:
            repeat_count = int(count_str) if count_str and int(count_str) > 0 else 1
        except ValueError:
            repeat_count = 1

        print(f"\n>>> 正在處理帳號: {phone} (產出條碼並執行現金儲值)")

        try:
            client.handshake()

            # 1. 刷新 Login Token
            res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                        {"Timestamp": client._get_timestamp(), "CellPhone": phone})
            new_token = res_token.get("EncData", {}).get("LoginTokenID", "").split(',')[0]

            # 2. 發送驗證簡訊
            res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                      {"Timestamp": client._get_timestamp(), "CellPhone": phone,
                                       "SMSAuthType": 5, "UserCode": "", "LoginTokenID": new_token})
            new_auth = res_sms.get("EncData", {}).get("AuthCode", "")

            # 3. 登入
            client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                            {"Timestamp": client._get_timestamp(), "LoginType": "1",
                             "UserCode": user_code, "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

            time.sleep(1)

            # 4. 產生通路儲值條碼
            topup_req_payload = {
                "Amount": 10000,
                "TopUpType": 1,
                "Timestamp": client._get_timestamp()
            }

            for i in range(repeat_count):
                res_topup = client.call_api(client.payment_url, "app/TopUpPayment/GetTopUpBarCode", topup_req_payload)
                enc_res = res_topup.get("EncData", {})
                new_barcode = enc_res.get("TopUpBarcode") or enc_res.get("Barcode", "")

                if new_barcode:
                    print(f"   [# {i + 1}] 成功產出條碼: {new_barcode}")
                    updated_rows.append([user_code, phone, new_token, new_auth, new_barcode, str(repeat_count)])

                    # --------------------------------------------------------
                    # 接續執行市場儲值 API (SETTopUp)
                    # --------------------------------------------------------
                    print(f"       正在執行現金儲值 (SETTopUp)...")
                    now = datetime.now()
                    trade_no = f"Sample{now.strftime('%Y%m%d%H%M%S')}{i}"
                    trade_date = now.strftime("%Y/%m/%d %H:%M:%S")

                    market_payload = {
                        "PlatformID": "10000266",
                        "MerchantID": "10000266",
                        "Ccy": "TWD",
                        "TopUpAmt": "10000",
                        "OPSeq": trade_no,
                        "StoreId": "982351",
                        "StoreName": "鑫和睦",
                        "PosNo": "01",
                        "OPTime": trade_date,
                        "CorpID": "22555003",
                        "PaymentNo": "038",
                        "Remark": "123456",
                        "Itemlist": [{}],
                        "BuyerID": new_barcode,
                    }

                    # 使用市場專用的 AES 與 RSA 簽章
                    json_str = json.dumps(market_payload, ensure_ascii=False, separators=(',', ':'))
                    market_enc_data = CryptoHelper.aes_encrypt(json_str, MARKET_AES_KEY, MARKET_AES_IV)

                    # 導入市場專用私鑰進行簽章
                    market_rsa_key = RSA.import_key(MARKET_PRIVATE_KEY)
                    market_sig = client.crypto.sign_sha256(market_enc_data, custom_priv_key=market_rsa_key)

                    market_headers = {
                        'X-iCP-EncKeyID': MARKET_ENC_KEY_ID,
                        'X-iCP-Signature': market_sig,
                        'Content-Type': 'application/x-www-form-urlencoded',
                    }

                    market_url = "https://icp-payment-stage.icashpay.com.tw/api/V2/Payment/Pos/SETTopUp"
                    market_body = f"EncData={quote(market_enc_data)}"

                    try:
                        m_resp = requests.post(market_url, data=market_body, headers=market_headers).json()
                        if "EncData" in m_resp:
                            m_decrypted = CryptoHelper.aes_decrypt(m_resp["EncData"], MARKET_AES_KEY, MARKET_AES_IV)
                            m_data = json.loads(m_decrypted)

                            # 儲存結果
                            with open(REFUND_FILE, 'a', encoding='utf-8') as rf:
                                rf.write(
                                    f"BuyerID: {new_barcode}\nTopUpAmt: 10000\nOPSeq: {m_data.get('OPSeq')}\nBankSeq: {m_data.get('BankSeq')}\n\n")
                            print(f"       ✅ 儲值成功！結果已存入 {REFUND_FILE}")
                        else:
                            print(f"       ❌ 儲值 API 失敗: {m_resp}")
                    except Exception as me:
                        print(f"       ❌ 執行儲值時發生報錯: {me}")
                else:
                    print(f"   [# {i + 1}] ⚠️ 取得條碼失敗")
                    updated_rows.append([user_code, phone, new_token, new_auth, "", str(repeat_count)])

                if repeat_count > 1: time.sleep(1)

            # 查詢帳戶餘額
            try:
                coins_info = client.get_total_coins()
                print(f"   💰 帳戶餘額查詢結果: {coins_info}")
            except Exception as e:
                print(f"   ⚠️ 查詢帳戶餘額失敗: {e}")

        except Exception as e:
            print(f"❌ 帳號 {phone} 系統報錯: {e}")
            updated_rows.append([user_code, phone, current_token, current_auth, current_barcode, count_str])

    # 寫回檔案
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header + "\n")
        for row in updated_rows:
            f.write(",".join(row) + "\n")

    print(f"\n處理完畢。")


if __name__ == '__main__':
    process_accounts()