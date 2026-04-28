import json
import base64
import random
import re
from datetime import datetime
from locust import HttpUser, task, between, SequentialTaskSet
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# --- 1. 加密輔助類別 (保持一致性) ---
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
        self._rsa_public_key = RSA.import_key(pem_key)

    def import_rsa_private(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PRIVATE KEY-----\n{pem_key}\n-----END PRIVATE KEY-----"
        self._rsa_private_key = RSA.import_key(pem_key)

    def rsa_encrypt_with_public(self, data):
        key_size = self._rsa_public_key.size_in_bytes()
        max_chunk = key_size - 11
        cipher = PKCS1_v1_5.new(self._rsa_public_key)
        data_bytes = data.encode('utf-8')
        chunks = [cipher.encrypt(data_bytes[i:i + max_chunk]) for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join(chunks)).decode('utf-8')

    def rsa_decrypt_with_private(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size = self._rsa_private_key.size_in_bytes()
        cipher = PKCS1_v1_5.new(self._rsa_private_key)
        decrypted_chunks = [cipher.decrypt(encrypted_bytes[i:i + key_size], b'error_sentinel')
                            for i in range(0, len(encrypted_bytes), key_size)]
        return b''.join(decrypted_chunks).decode('utf-8')

    def sign_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._rsa_private_key).sign(h)
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


# --- 2. 壓測行為序列 ---
class PaymentFlow(SequentialTaskSet):
    @task
    def p0037_parser_qrcode(self):
        """ 第一步：解析 QrCode 並提取 MerchantTradeNo """
        payload = {
            "MerchantQRcode": self.user.account_info['TradeToken'],
            "Timestamp": self.user._ts()
        }
        resp = self.user.call_api(self.user.plus_url, "app/Payment/ParserQrCode", payload)

        self.user.last_trade_no = None
        if resp and resp.get("RtnCode") == 1:
            try:
                # 解析 RtnValue 內的 JSON 字串
                rtn_val = json.loads(resp["EncData"].get("RtnValue"))
                self.user.last_trade_no = rtn_val.get("MerchantTradeNo")
            except Exception as e:
                print(f"解析單號失敗: {e}")

    @task
    def p0018_do_payment(self):
        """ 第二步：執行支付 API """
        if not getattr(self.user, 'last_trade_no', None):
            return

        payload = {
            "Amount": "5",
            "MerchantID": "10000236",
            "MerchantTradeNo": self.user.last_trade_no,
            "Mission": "",
            "PayID": self.user.account_info['PayID'],
            "StoreID": "Dev2-Test",
            "StoreName": "Dev2-Test",
            "Team_number": "",
            "Timestamp": self.user._ts()
        }
        self.user.call_api(self.user.payment_url, "app/Payment/DoQRPayment", payload)


# --- 3. Locust 使用者設定 ---
class IcashPayUser(HttpUser):
    tasks = [PaymentFlow]
    wait_time = between(1, 2)

    member_url = "https://icp-member-stage.icashpay.com.tw/"
    payment_url = "https://icp-payment-stage.icashpay.com.tw/"
    plus_url = "https://icp-plus-stage.icashpay.com.tw/"

    def on_start(self):
        self.crypto = CryptoHelper()
        self.aes_info = {}
        self.last_trade_no = None
        self.load_account()
        self.handshake()

    def load_account(self):
        path = r"C:\icppython\account.txt"
        with open(path, 'r', encoding='utf-8') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            row = random.choice(lines[1:]).split(',')
            self.account_info = {"PayID": row[4], "TradeToken": row[5]}

    def _ts(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def handshake(self):
        # 建立加密連線
        r1 = self.client.post(f"{self.member_url}api/member/Certificate/GetDefaultPucCert").json()
        kp = self.crypto.generate_rsa_key()
        self.crypto.import_rsa_private(kp['private_key'])
        self.crypto.import_rsa_public(r1['DefaultPubCert'])

        enc = self.crypto.rsa_encrypt_with_public(
            json.dumps({'ClientPubCert': "".join(kp['public_key'].splitlines()[1:-1]), 'Timestamp': self._ts()}))
        sig = self.crypto.sign_sha256(enc)
        r2 = self.client.post(f"{self.member_url}api/member/Certificate/ExchangePucCert", data={'EncData': enc},
                              headers={'X-iCP-DefaultPubCertID': str(r1['DefaultPubCertID']),
                                       'X-iCP-Signature': sig}).json()

        exch = json.loads(self.crypto.rsa_decrypt_with_private(r2['EncData']))
        self.crypto.import_rsa_public(exch['ServerPubCert'])

        enc_aes = self.crypto.rsa_encrypt_with_public(json.dumps({'Timestamp': self._ts()}))
        sig_aes = self.crypto.sign_sha256(enc_aes)
        r3 = self.client.post(f"{self.member_url}api/member/Certificate/GenerateAES", data={'EncData': enc_aes},
                              headers={'X-iCP-ServerPubCertID': str(exch['ServerPubCertID']),
                                       'X-iCP-Signature': sig_aes}).json()

        res_aes = json.loads(self.crypto.rsa_decrypt_with_private(r3['EncData']))
        self.aes_info = {'id': res_aes['EncKeyID'], 'key': res_aes['AES_Key'], 'iv': res_aes['AES_IV']}

    def call_api(self, base_url, action, payload):
        enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                           self.aes_info['iv'])
        sig = self.crypto.sign_sha256(enc_data)
        headers = {'X-iCP-EncKeyID': str(self.aes_info['id']), 'X-iCP-Signature': sig}

        with self.client.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers,
                              catch_response=True) as response:
            try:
                res_j = response.json()
                if "EncData" in res_j and isinstance(res_j['EncData'], str):
                    dec = self.crypto.aes_decrypt(res_j['EncData'], self.aes_info['key'], self.aes_info['iv'])
                    res_j['EncData'] = json.loads(dec) if dec else {}
                return res_j
            except Exception as e:
                response.failure(f"API Error: {e}")
                return {}