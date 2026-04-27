import json
import base64
import csv
import random
from queue import Queue
from datetime import datetime
from locust import HttpUser, task, between
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# --- 配置區 ---
ACCOUNT_FILE = r'C:\icppython\account.txt'

# 【第一組金鑰】用於被掃付款 (POS_SETPay)
POS_CONFIG = {
    "AES_KEY": "VhoGVCInVF2UJ1cQBVZCF48lGUVIoCng",
    "AES_IV": "z3P4Se8qTFE0F1xI",
    "KEY_ID": "288768",
    "PRIVATE_KEY": """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEA0hXyO7E10c4WR/S1XUFUyvlLS8wX/3RoL9nE4kwWJC+nTy8AFSVBgNz2KPnv3If+q8lG3bqq6TCiBmZxP33hbQH1H/cZPHag644nHlHc0/ZSunXB92jprH4xf96wfev12wqrMbCnYKytInEJnuHN+n3eq0LuyQ/WRcPVROJWxYFUO+uGLbFohtmppb0f/cSKOr0hVP15qZAEVSQwYHhu1CJAI/XoRLkZd87A2KHzvVJ2qkbjRbzXemRToE0v3GrWoUoBIMW3cJxgKieMW/HhQHfnz8njTf4nYlA4OSi2U43OA3Z9T+9gB5I8FvfOokt/LfhvO5q/l7QWB+yaX2hvuQIDAQABAoIBAAd57PYnWws1mpDiej7Ql6AmiYGvyG3YmmmThiBohUQx5vIYMdhOzFs14dO4+0p9k3hRECLNZQ4p4yY3qJGSHP7YWj0SOdVvQlBHrYg0cReg9TY6ARZZJzGyhvfuOJkul7/9C/UXfIlh88JdQ/KhxgcDSjSNi/pfRCiU7MbICD78h/pCS1zIWHaICZ2aL5rV2o5JwCcvDP8p3F+LFW/5u5kK0D0Pd29FXhf5MKHC4Mgrn2I44Uyhdud2Mf7wdvYvvcv2Nzn/EvM7uYZpkEyC3Y1Ow037fZjO3pVCVRt8Mbo4B75ORqXQnr1SbKXWXM/unUEIfMhsBRhx/diDCO8xyiECgYEA8UXIvYWREf+EN5EysmaHcv1jEUgFym8xUiASwwAv+LE9jQJSBiVym13rIGs01k1RN9z3/RVc+0BETTy9qEsUzwX9oTxgqlRk8R3TK7YEg6G/W/7D5DDM9bS/ncU7PlKA/FaEasHCfjs0IY5yJZFYrcA2QvvCl1X1NUZ4Hyumk1ECgYEA3ujTDbDNaSy/++4W/Ljp5pIVmmO27jy30kv1d3fPG6HRtPvbwRyUk/Y9PQpVpd7Sx/+GN+95Z3/zy1IHrbHN5SxE+OGzLrgzgj32EOU+ZJk5uj9qNBkNXh5prcOcjGcMcGL9OAC2oaWaOxrWin3fAzDsCoGrlzSzkVANnBRB6+kCgYEA2EaA0nq3dxW/9HugoVDNHCPNOUGBh1wzLvX3O3ughOKEVTF+S2ooGOOQkGfpXizCoDvgxKnwxnxufXn0XLao+YbaOz0/PZAXSBg/IlCwLTrBqXpvKM8h+yLCHXAeUhhs7UW0v2neqX7ylR32bnyirGW/fj3lyfjQrKf1p6NeV3ECgYB2X+fspk5/Iu+VJxv3+27jLgLg6UE1BPONbx8c4XgPsYB+/xz1UWsppCNjLgDLxCflY7HwNHEhYJakC5zeRcUUhcze6mTQU6uu556r3EGlBKXeXVzV69Pofngaef3Bpdu6NydHvUE/WIUuDBOQmkV7GVjQP4pTEv6lFYEUuMFFOQKBgHfINuaiIlITl/u59LPrvhTZoq6qg7N/3wVeAjYvbpv+b2cFgvOMQAr+S8eCDzijy2z4MENBTr/q6mkKe4NHFGtodP+bjSYEG+GnBEG+EUpAx3Wh/BL2f/sIiSOH9ODB6B847F+apa0OTawmslgGna9/985egGMto9g16EQ4ib1M
-----END PRIVATE KEY-----"""
}

# 【第二組金鑰】用於主掃產生 QR (CreateTradeICPO)
QR_CONFIG = {
    "AES_KEY": "Nu52fAODFfP2xM2dGT4LLoS10ZldZzoh",
    "AES_IV": "KJUYfTyo7Emy2sT9",
    "KEY_ID": "289774",
    "PRIVATE_KEY": """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEAzk25wl5iqDJARbX4QsaBFeWMDmwJJuof39DlmIOle+ghPNT5DFaZv/oo9h53W0+MT+bfvsLknzv/wJnKCajbBmi6A8yh5s0imEOLt6kZTruIVG3KM4d+K0r5HhIJ1CYXGiQh0s6KcY88w7oYlgCRvCGcxsTe8I93THZT5ZRXr8MRxZmVIdA6kifYFztA5JbVt5Gw56dHd+eSjXobXkdmimsn0RuQEhTwnpgrxI0dJM+kO4IqKfNItMiDv48kLCbIuhjw1HSFKSKMbOpf/r1j1ApCKS03TXpDXg2IpgTLLiYNYjTipMWS78qnrZywLeqTS8JnwMkdpVxjy8i+1W4RPwIDAQABAoIBAEO6gbcdfH8ijDY2oOvvNlbFdv8PGcwUReWZM58n7Q6qLStG8gJKdgxwKL1wUBgCnBppPeBnJF5geLy24HzeWhWXESaJKkfW5boeRsLDeaL+7ylkp+LV4yZ8ZR+ppV9oJ+J1pUMLeqkAcN8C++pXAoFEea9J17UbLHvGRxHSax0wsvXenm7yESKZ8euJHdDo7XQ8f+saqsDHN9sJ1Hw8PH+YWKMTc0KYyLkXH6NkPHJPcgziPX31opyuvQPSrOJ9RjERqiNYU6LMeORMdSbgQnR+v7HVuwuX8MDaEaAId8ykJ7UBP7qodSfHUO9e+0o4bYOgaoWHzonV6gQuKjnNR3kCgYEA4A2ekYUQnHcqn2+jzJSNVM69ApbluDV1uL63J1npWgTvKBnlPczVhg25G595L1l9YvrIRUawbad9Q537KIIAH6F9FfSl9b2vlXo0D0PYR0JRwDLlVXMwJZ40Ee6slkgsmeDOto+yOk/lk61XMXpEvDkKei5ov57C6cVmFJcsotcCgYEA67g2K1oou6i3SchaehCxbue/owK/ydeLPYr983yfMiDZfOA4D3v2RF4aSmMnPe3sUq4ZRew5nyVJ8f5f14Dirs2jglaQsdopkrNroTNuyLZUZfI9/v/6VVRNTQXigPOcS2NbLmXN0fMi6VxlU8IN3vkXE+cyOv0/eRV258IgH9kCgYAYvqhSngWVojuc3DGU+JsbULHjRVMdoxnbS4Ti3bU98emP3jxJNQQoB//3owc5SYLlmZjgvcvicGsPOrVwZdspoyYzdI+XsllgAt0ZCn8qb5KjzXsyksQwg2ZwzJFXD6WNYRyzYO9oLUbHpo9IsZ5Bw3L6x4FeGGSieOCrSX7uhQKBgDViAJKM1pC5Qtko0KS4Rxaw0UufgcO6VsRXR+/ulzcJDXgkZ03KaxlMnnOeRPLXgR+wYfTd7KbIERkG3Lm3bJ7d31vTMu20VJnunD9joIFAGZkE5Vlsq0rLzr3UyVke0pSYKbw2PgiAIbXrwN7ZIb8PdlSBlXSaiddoLweJhTDxAoGBAKgAyumIYzjryg6mHFemWVidfKMK9UjywGDz0UXxP3UBk3ME8aIw0ynqyjCK8ULspo3dmGA4ze32fKo97xTzUhtx9YkcvXQe8axtqkBLDROHvxUvnhyIZgexey6I+w023LbIbUUr2F/cB0YOP5kidjwrCpTqat0jcir4T26VetRN
-----END PRIVATE KEY-----"""
}


# --- 工具函數 ---
def encrypt_aes(data, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    return base64.b64encode(cipher.encrypt(pad(data.encode('utf-8'), AES.block_size))).decode('utf-8')


def decrypt_aes(enc_data, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    return unpad(cipher.decrypt(base64.b64decode(enc_data)), AES.block_size).decode('utf-8')


def sign_data(data, priv_key_pem):
    key = RSA.import_key(priv_key_pem)
    h = SHA256.new(data.encode('utf-8'))
    return base64.b64encode(pkcs1_15.new(key).sign(h)).decode('utf-8')


# --- 讀取 Barcode 佇列 ---
barcode_queue = Queue()
try:
    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bc = row.get('Barcode')
            if bc and bc not in ["", "ERROR", "FAIL"]:
                barcode_queue.put(bc)
except Exception as e:
    print(f"CSV Error: {e}")


# --- Locust 壓測主體 ---
class ICPPaymentUser(HttpUser):
    wait_time = between(1, 3)
    host = "https://icp-payment-stage.icashpay.com.tw"

    @task(3)
    def pos_payment_barcode(self):
        """【任務 1】使用 POS 金鑰進行被掃"""
        try:
            current_barcode = barcode_queue.get_nowait()
        except:
            return

        now = datetime.now()
        trade_no = f"LPOS{now.strftime('%Y%m%d%H%M%S%f')}{random.randint(10, 99)}"[:20]

        payload = {
            "PlatformID": "10000266",
            "MerchantID": "10000266",
            "Ccy": "TWD", "TxAmt": "1",
            "StoreId": "217477", "StoreName": "壓測POS店",
            "PosNo": "01", "OPSeq": trade_no,
            "OPTime": now.strftime('%Y/%m/%d %H:%M:%S'),
            "ItemAmt": "1", "BonusType": "ByWallet",
            "PaymentNo": "038", "BuyerID": current_barcode,
            "Itemlist": [{"ItemName": "商品", "Quantity": "1", "UnitPrice": "1"}],
        }

        self._send_request("/api/V2/Payment/Pos/SETPay", payload, POS_CONFIG, "POS_SETPay")
        barcode_queue.task_done()

    @task(1)
    def cashier_create_qr(self):
        """【任務 2】使用 QR 專用金鑰產出訂單"""
        now = datetime.now()
        merchant_trade_no = f"LQR{now.strftime('%Y%m%d%H%M%S%f')}{random.randint(10, 99)}"[:20]

        payload = {
            "PlatformID": "10000236",
            "MerchantID": "10000236",
            "MerchantTradeNo": merchant_trade_no,
            "StoreID": "Dev2-Test",
            "StoreName": "主掃壓測店",
            "TradeMode": "2",
            "MerchantTradeDate": now.strftime('%Y/%m/%d %H:%M:%S'),
            "TotalAmount": "500",
            "ItemAmt": "500",
            "CallbackURL": "https://www.google.com",
            "Item": [{"ItemNo": "QR01", "ItemName": "壓測商品", "Quantity": "1"}]
        }

        self._send_request("/api/V2/Payment/Cashier/CreateTradeICPO", payload, QR_CONFIG, "QR_Create")

    def _send_request(self, endpoint, payload, config, name):
        json_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
        enc_data = encrypt_aes(json_str, config["AES_KEY"], config["AES_IV"])
        signature = sign_data(enc_data, config["PRIVATE_KEY"])

        headers = {
            'X-iCP-EncKeyID': config["KEY_ID"],
            'X-iCP-Signature': signature,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        with self.client.post(endpoint, headers=headers, data={'EncData': enc_data}, name=name,
                              catch_response=True) as response:
            if response.status_code == 200:
                try:
                    resp_json = response.json()
                    if 'EncData' in resp_json:
                        # 使用正確的 AES 金鑰解密回傳值
                        dec_raw = decrypt_aes(resp_json['EncData'], config["AES_KEY"], config["AES_IV"])
                        res_data = json.loads(dec_raw)

                        if str(res_data.get('RtnCode')) == "1" or res_data.get('Status') == "200":
                            response.success()
                        else:
                            response.failure(f"Biz Error: {res_data}")
                    else:
                        response.failure(f"No EncData: {resp_json}")
                except Exception as e:
                    response.failure(f"Decrypt Fail: {str(e)}")
            else:
                response.failure(f"HTTP {response.status_code}")