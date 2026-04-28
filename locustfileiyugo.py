import json
import base64
import random
import re
import os
import time
from datetime import datetime
from locust import HttpUser, task, between, SequentialTaskSet
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
        return {'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
                'public_key': key.publickey().export_key(format='PEM').decode('utf-8')}

    def import_rsa_public(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._rsa_public_key = RSA.import_key(pem_key)[cite: 35]

    def import_rsa_private(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PRIVATE KEY-----\n{pem_key}\n-----END PRIVATE KEY-----"
        self._rsa_private_key = RSA.import_key(pem_key)

    def rsa_encrypt_with_public(self, data):
        cipher = PKCS1_v1_5.new(self._rsa_public_key)[cite: 36]
        data_bytes = data.encode('utf-8')
        key_size = self._rsa_public_key.size_in_bytes()
        max_chunk = key_size - 11
        chunks = [cipher.encrypt(data_bytes[i:i + max_chunk]) for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join(chunks)).decode('utf-8')

    def rsa_decrypt_with_private(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = PKCS1_v1_5.new(self._rsa_private_key)[cite: 37]
        key_size = self._rsa_private_key.size_in_bytes()
        chunks = [cipher.decrypt(encrypted_bytes[i:i + key_size], b'error') for i in
                  range(0, len(encrypted_bytes), key_size)]
        return b''.join(chunks).decode('utf-8')

    def sign_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        return base64.b64encode(pkcs1_15.new(self._rsa_private_key).sign(h)).decode('utf-8')[cite: 38]

    @staticmethod
    def aes_encrypt(data, key, iv):
        cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
        return base64.b64encode(cipher.encrypt(pad(data.encode('utf-8'), 16))).decode('utf-8')

    @staticmethod
    def aes_decrypt(enc_data, key, iv):
        try:
            cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))[cite: 39]
            dec = unpad(cipher.decrypt(base64.b64decode(enc_data)), 16).decode('utf-8')
            match = re.search(r'\{.*\}', dec, re.DOTALL)
            return match.group() if match else dec
        except:
            return None


# --- 2. 壓測行為序列 (P0037 -> P0018) ---
class PaymentFlow(SequentialTaskSet):
    @task
    def p0037_parser_qrcode(self):
        """ 第一步：API P0037 解析 QrCode 並提取 MerchantTradeNo """
        # 確保每次解析前都嘗試載入最新 Token
        self.user.load_local_account()[cite: 46]

        if not self.user.account_info: return

        payload = {
            "MerchantQRcode": self.user.account_info['TradeToken'],
            "Timestamp": self.user._ts()[cite: 40]
        }
        resp = self.user.call_api(self.user.plus_url, "app/Payment/ParserQrCode", payload)

        self.user.last_trade_no = None

        if resp and resp.get("RtnCode") == 1:
            try:
                # 解析 RtnValue JSON 字串以取得商戶單號
                rtn_val_str = resp.get("EncData", {}).get("RtnValue")
                if rtn_val_str:
                    rtn_data = json.loads(rtn_val_str)[cite: 42]
                    self.user.last_trade_no = rtn_data.get("MerchantTradeNo")[cite: 42]
                    if self.user.last_trade_no:
                        print(f"[*] 解析成功 -> 單號: {self.user.last_trade_no}")
            except Exception as e:
                print(f"[-] RtnValue 解析異常: {e}")
        else:
            print(f"[-] P0037 失敗: {resp.get('RtnMsg')}")

    @task
    def p0018_do_payment(self):
        """ 第二步：API P0018 執行確認支付 """
        if not getattr(self.user, 'last_trade_no', None): [cite: 43]
        return

    payload = {
        "Amount": "5",
        "MerchantID": "10000236",
        "MerchantTradeNo": self.user.last_trade_no, [cite: 43]
    "Mission": "",
    "PayID": self.user.account_info['PayID'], [cite: 47]
    "StoreID": "",
    "StoreName": "",
    "Team_number": "",
    "Timestamp": self.user._ts()[cite: 44]
    }
    resp = self.user.call_api(self.user.payment_url, "app/Payment/DoQRPayment", payload)

    if resp and resp.get("RtnCode") == 1:
        print(f"[SUCCESS] 付款完成! 單號: {self.user.last_trade_no}")
        # 強制清除單號並結束本次序列，迫使 User 重新交握與挑選 Token
        self.user.last_trade_no = None
        self.interrupt()
    else:
        print(f"[FAIL] 付款失敗: {resp.get('RtnMsg')}")


# --- 3. Locust 使用者設定 ---
class IcashPayUser(HttpUser):
    host = "https://icp-member-stage.icashpay.com.tw"
    tasks = [PaymentFlow]
    wait_time = between(1, 3)

    member_url = "https://icp-member-stage.icashpay.com.tw/"
    payment_url = "https://icp-payment-stage.icashpay.com.tw/"
    plus_url = "https://icp-plus-stage.icashpay.com.tw/"

    def on_start(self):
        self.crypto = CryptoHelper()
        self.aes_info = {}
        self.last_trade_no = None
        self.load_local_account()[cite: 46]
        self.handshake()[cite: 48]

    def load_local_account(self):
        """ 從產出的檔案隨機讀取資料 [cite: 46, 47] """
        try:
            path = r"C:\icppython\account.txt"
            with open(path, 'r', encoding='utf-8') as f:
                [cite: 46]
            lines = [l.strip() for l in f.readlines() if l.strip()]
            if len(lines) > 1:
                row = random.choice(lines[1:]).split(',')[cite: 46]
                # 確保索引正確：PayID(4), TradeToken(5)
                self.account_info = {"PayID": row[4], "TradeToken": row[5]}[cite: 47]

    except Exception as e: print(f"[!] 檔案讀取失敗: {e}")


def _ts(self):
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")[cite: 55]


def handshake(self):
    """ 加密連線初始化 (AES 交換) [cite: 48, 49, 50, 51] """
    r1 = self.client.post(f"{self.member_url}api/member/Certificate/GetDefaultPucCert").json()[cite: 48]
    kp = self.crypto.generate_rsa_key()
    self.crypto.import_rsa_private(kp['private_key'])
    self.crypto.import_rsa_public(r1['DefaultPubCert'])

    enc = self.crypto.rsa_encrypt_with_public(
        json.dumps({'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._ts()}))
    r2 = self.client.post(f"{self.member_url}api/member/Certificate/ExchangePucCert",
                          data={'EncData': enc}, headers={'X-iCP-DefaultPubCertID': str(r1['DefaultPubCertID']),
                                                          'X-iCP-Signature': self.crypto.sign_sha256(enc)}).json()[
         cite: 49]

    exch_res = json.loads(self.crypto.rsa_decrypt_with_private(r2['EncData']))[cite: 50]
    self.crypto.import_rsa_public(exch_res['ServerPubCert'])

    enc_aes = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._ts()}))
    r3 = self.client.post(f"{self.member_url}api/member/Certificate/GenerateAES",
                          data={'EncData': enc_aes}, headers={'X-iCP-ServerPubCertID': str(exch_res['ServerPubCertID']),
                                                              'X-iCP-Signature': self.crypto.sign_sha256(
                                                                  enc_aes)}).json()[cite: 51]

    res_aes = json.loads(self.crypto.rsa_decrypt_with_private(r3['EncData']))
    self.aes_info = {'id': res_aes['EncKeyID'], 'key': res_aes['AES_Key'], 'iv': res_aes['AES_IV']}


def call_api(self, base_url, action, payload):
    """ 執行加密 API 並自動處理回應 [cite: 52, 53, 54] """
    enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                       self.aes_info['iv'])[cite: 52]
    headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': self.crypto.sign_sha256(enc_data)}[
              cite: 52]
    with self.client.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers,
                          catch_response=True) as response:
        [cite: 53]
    try:
        res_j = response.json()
        if "EncData" in res_j and isinstance(res_j['EncData'], str):
            dec = self.crypto.aes_decrypt(res_j['EncData'], self.aes_info['key'], self.aes_info['iv'])[cite: 54]
            res_j['EncData'] = json.loads(dec) if dec else dec
        return res_j
    except Exception as e:
        response.failure(f"API Error: {e}")
        return {}