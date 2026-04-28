import json
import base64
import csv
from queue import Queue
from datetime import datetime
from locust import HttpUser, task, between
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

# --- 配置區 ---
AES_KEY = "VhoGVCInVF2UJ1cQBVZCF48lGUVIoCng"
AES_IV = "z3P4Se8qTFE0F1xI"
ACCOUNT_FILE = r'C:\icppython\account.txt'

CLIENT_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEowIBAAKCAQEA0hXyO7E10c4WR/S1XUFUyvlLS8wX/3RoL9nE4kwWJC+nTy8AFSVBgNz2KPnv3If+q8lG3bqq6TCiBmZxP33hbQH1H/cZPHag644nHlHc0/ZSunXB92jprH4xf96wfev12wqrMbCnYKytInEJnuHN+n3eq0LuyQ/WRcPVROJWxYFUO+uGLbFohtmppb0f/cSKOr0hVP15qZAEVSQwYHhu1CJAI/XoRLkZd87A2KHzvVJ2qkbjRbzXemRToE0v3GrWoUoBIMW3cJxgKieMW/HhQHfnz8njTf4nYlA4OSi2U43OA3Z9T+9gB5I8FvfOokt/LfhvO5q/l7QWB+yaX2hvuQIDAQABAoIBAAd57PYnWws1mpDiej7Ql6AmiYGvyG3YmmmThiBohUQx5vIYMdhOzFs14dO4+0p9k3hRECLNZQ4p4yY3qJGSHP7YWj0SOdVvQlBHrYg0cReg9TY6ARZZJzGyhvfuOJkul7/9C/UXfIlh88JdQ/KhxgcDSjSNi/pfRCiU7MbICD78h/pCS1zIWHaICZ2aL5rV2o5JwCcvDP8p3F+LFW/5u5kK0D0Pd29FXhf5MKHC4Mgrn2I44Uyhdud2Mf7wdvYvvcv2Nzn/EvM7uYZpkEyC3Y1Ow037fZjO3pVCVRt8Mbo4B75ORqXQnr1SbKXWXM/unUEIfMhsBRhx/diDCO8xyiECgYEA8UXIvYWREf+EN5EysmaHcv1jEUgFym8xUiASwwAv+LE9jQJSBiVym13rIGs01k1RN9z3/RVc+0BETTy9qEsUzwX9oTxgqlRk8R3TK7YEg6G/W/7D5DDM9bS/ncU7PlKA/FaEasHCfjs0IY5yJZFYrcA2QvvCl1X1NUZ4Hyumk1ECgYEA3ujTDbDNaSy/++4W/Ljp5pIVmmO27jy30kv1d3fPG6HRtPvbwRyUk/Y9PQpVpd7Sx/+GN+95Z3/zy1IHrbHN5SxE+OGzLrgzgj32EOU+ZJk5uj9qNBkNXh5prcOcjGcMcGL9OAC2oaWaOxrWin3fAzDsCoGrlzSzkVANnBRB6+kCgYEA2EaA0nq3dxW/9HugoVDNHCPNOUGBh1wzLvX3O3ughOKEVTF+S2ooGOOQkGfpXizCoDvgxKnwxnxufXn0XLao+YbaOz0/PZAXSBg/IlCwLTrBqXpvKM8h+yLCHXAeUhhs7UW0v2neqX7ylR32bnyirGW/fj3lyfjQrKf1p6NeV3ECgYB2X+fspk5/Iu+VJxv3+27jLgLg6UE1BPONbx8c4XgPsYB+/xz1UWsppCNjLgDLxCflY7HwNHEhYJakC5zeRcUUhcze6mTQU6uu556r3EGlBKXeXVzV69Pofngaef3Bpdu6NydHvUE/WIUuDBOQmkV7GVjQP4pTEv6lFYEUuMFFOQKBgHfINuaiIlITl/u59LPrvhTZoq6qg7N/3wVeAjYvbpv+b2cFgvOMQAr+S8eCDzijy2z4MENBTr/q6mkKe4NHFGtodP+bjSYEG+GnBEG+EUpAx3Wh/BL2f/sIiSOH9ODB6B847F+apa0OTawmslgGna9/985egGMto9g16EQ4ib1M
-----END PRIVATE KEY-----"""

# --- 工具函數 ---

def encrypt_aes_cbc_256(data, key, iv):
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    padded_data = pad(data.encode('utf-8'), AES.block_size)
    return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

def decrypt_aes_cbc_256(enc_data, key, iv):
    encrypted_bytes = base64.b64decode(enc_data)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CBC, iv.encode('utf-8'))
    return unpad(cipher.decrypt(encrypted_bytes), AES.block_size).decode('utf-8')

def sign_data(data, private_key_pem):
    key = RSA.import_key(private_key_pem)
    h = SHA256.new(data.encode('utf-8'))
    return base64.b64encode(pkcs1_15.new(key).sign(h)).decode('utf-8')

# --- 讀取 account.txt ---
barcode_queue = Queue()
with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        barcode_queue.put(row['Barcode'])

# --- Locust 測試主體 ---

class ICPPaymentUser(HttpUser):
    # 每個虛擬用戶執行完一次任務後隨機等待 1 到 3 秒
    wait_time = between(1, 3)
    host = "https://icp-payment-stage.icashpay.com.tw"

    @task
    def post_payment(self):
        # 從佇列中取得一個 Barcode，如果沒了就停止
        try:
            current_barcode = barcode_queue.get_nowait()
        except:
            print("所有 Barcode 已處理完畢。")
            self.environment.runner.quit()
            return

        now = datetime.now()
        trade_no = f"Locust{now.strftime('%Y%m%d%H%M%S%f')}" # 增加微秒確保壓測時不重複
        trade_date = now.strftime('%Y/%m/%d %H:%M:%S')

        payload = {
            "PlatformID": "10000266",
            "MerchantID": "10000266",
            "Ccy": "TWD",
            "TxAmt": "1",
            "NonRedeemAmt": "",
            "NonPointAmt": "",
            "StoreId": "217477",
            "StoreName": "見晴",
            "PosNo": "01",
            "OPSeq": trade_no,
            "OPTime": trade_date,
            "ReceiptNo": "",
            "ReceiptReriod": "",
            "TaxID": "",
            "CorpID": "22555003",
            "Vehicle": "",
            "Donate": "",
            "ItemAmt": "1",
            "UtilityAmt": "",
            "CommAmt": "",
            "ExceptAmt1": "",
            "ExceptAmt2": "",
            "BonusType": "ByWallet",
            "BonusCategory": "",
            "BonusID": "",
            "PaymentNo": "038",
            "Remark": "LocustTest",
            "ReceiptPrint": "N",
            "Itemlist": [{}],
            "BuyerID": current_barcode,
        }

        # 加密與簽名
        json_str = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
        enc_data = encrypt_aes_cbc_256(json_str, AES_KEY, AES_IV)
        signature = sign_data(enc_data, CLIENT_PRIVATE_KEY)

        headers = {
            'X-iCP-EncKeyID': '288768',
            'X-iCP-Signature': signature,
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        # 發送請求
        with self.client.post("/api/V2/Payment/Pos/SETPay",
                               headers=headers,
                               data={'EncData': enc_data},
                               catch_response=True) as response:
            if response.status_code == 200:
                try:
                    resp_json = response.json()
                    if 'EncData' in resp_json:
                        decrypted_res = decrypt_aes_cbc_256(resp_json['EncData'], AES_KEY, AES_IV)
                        # 成功解析則標記成功
                        response.success()
                    else:
                        response.failure("Response missing EncData")
                except Exception as e:
                    response.failure(f"Decryption Error: {str(e)}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

        # 標記該條碼處理完成
        barcode_queue.task_done()