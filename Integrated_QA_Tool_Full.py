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

    def sign_sha256(self, data):
        if not self._rsa_private_key: raise ValueError("尚未匯入私鑰")
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


# --- 2. API 客戶端 ---
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

    def call_api(self, base_url, action, payload, custom_key_id=None):
        enc_data = self.crypto.aes_encrypt(json.dumps(payload, ensure_ascii=False), self.aes_info['key'],
                                           self.aes_info['iv'])
        sig = self.crypto.sign_sha256(enc_data)
        key_id = custom_key_id if custom_key_id else self.aes_info['id']
        headers = {'X-iCP-EncKeyID': str(key_id), 'X-iCP-Signature': sig}
        try:
            r = self.session.post(f"{base_url}{action}", data={'EncData': enc_data}, headers=headers)
            resp = r.json()
            if "EncData" in resp and isinstance(resp['EncData'], str):
                decrypted = self.crypto.aes_decrypt(resp['EncData'], self.aes_info['key'], self.aes_info['iv'])
                if decrypted:
                    try:
                        resp['EncData'] = json.loads(decrypted)
                    except:
                        resp['EncData'] = decrypted
            return resp
        except Exception as e:
            return {"Status": "Error", "Message": str(e)}


# --- 3. 整合處理邏輯 ---
def process_integrated_tasks():
    ACCOUNT_FILE = r"C:\icppython\account.txt"
    print(f"[*] 正在檢查檔案: {ACCOUNT_FILE}")

    if not os.path.exists(ACCOUNT_FILE):
        print(f"[!] 錯誤: 找不到檔案 {ACCOUNT_FILE}")
        return

    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) <= 1:
        print("[!] 檔案中無資料列")
        return

    client = IcashPayClient()
    final_output_rows = []
    header_str = "UserCode,CellPhone,LoginTokenID,authcode,Barcode,Count,MerchantTradeNo"

    for idx, line in enumerate(lines[1:], 1):
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2: continue

        user_code, phone = parts[0], parts[1]
        try:
            count_val = int(parts[5]) if len(parts) > 5 and parts[5] else 1
        except:
            count_val = 1

        print(f"\n>>> [{idx}] 處理帳號: {phone} (展開產出 {count_val} 筆資料)")

        try:
            client.handshake()
            # 1. 登入
            res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                        {"Timestamp": client._get_timestamp(), "CellPhone": phone})
            token_enc = res_token.get("EncData", {})
            new_token = token_enc.get("LoginTokenID", "").split(',')[0] if isinstance(token_enc, dict) else ""

            res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                      {"Timestamp": client._get_timestamp(), "CellPhone": phone,
                                       "SMSAuthType": 5, "UserCode": "", "LoginTokenID": new_token})
            sms_enc = res_sms.get("EncData", {})
            new_auth = sms_enc.get("AuthCode", "") if isinstance(sms_enc, dict) else ""

            client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                            {"Timestamp": client._get_timestamp(), "LoginType": "1",
                             "UserCode": user_code, "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

            # 2. 搜尋 PayID
            res_pay = client.call_api(client.payment_url, "app/Payment/GetMemberPaymentInfo",
                                      {"Timestamp": client._get_timestamp(), "IsAutoPay": "false", "MerchantID": ""})
            p_data = res_pay.get("EncData", {})
            pay_id = None
            if isinstance(p_data, dict):
                for key in ["IcashpayList", "AllIcashpayList", "PaymentList"]:
                    target = p_data.get(key)
                    if isinstance(target, dict):
                        pay_id = target.get("PayID")
                    elif isinstance(target, list) and len(target) > 0:
                        pay_id = target[0].get("PayID")
                    if pay_id: break

            # 3. 核心展開邏輯：根據 Count 循環產出
            for i in range(count_val):
                current_bc = "FAIL_NO_PAYID"
                qr_status = "FAIL"

                # 被掃 Barcode
                if pay_id:
                    res_bc = client.call_api(client.payment_url, "app/Payment/CreateBarcode",
                                             {"PayID": pay_id, "PaymentType": "1",
                                              "Timestamp": client._get_timestamp()})
                    bc_enc = res_bc.get("EncData", {})
                    current_bc = bc_enc.get("Barcode", "FAIL") if isinstance(bc_enc, dict) else "FAIL"

                # 主掃 QR (iyugo 邏輯)
                # 強化 TradeNo 唯一性：日期+微秒+隨機數
                trade_no = f"ITG{datetime.now().strftime('%m%d%H%M%S%f')}{random.randint(100, 999)}"[:20]

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
                    "CallbackURL": "https://www.google.com",
                    "Item": [{"ItemNo": "001", "ItemName": "測試商品", "Quantity": "1"}]
                }

                # 呼叫 CreateTradeICPO API (KeyID: 289774)
                res_qr = client.call_api(client.payment_url, "api/V2/Payment/Cashier/CreateTradeICPO", qr_payload,
                                         custom_key_id="289774")
                if isinstance(res_qr.get("EncData"), dict):
                    qr_status = "OK"
                else:
                    qr_status = f"FAIL({res_qr.get('RtnCode', 'Err')})"

                print(f"  └─ [{i + 1}] Barcode: {current_bc} | QR: {qr_status} | TradeNo: {trade_no}")

                # 將每一筆獨立的資料存入列表，達成展開效果
                final_output_rows.append([user_code, phone, new_token, new_auth, current_bc, str(count_val), trade_no])

                # 給予微小延遲確保系統處理不重疊
                if count_val > 1: time.sleep(0.1)

        except Exception as e:
            print(f"❌ 嚴重錯誤: {phone} -> {str(e)}")

    # 4. 寫回 CSV (展開後的內容)
    print(f"\n[*] 正在寫入 {len(final_output_rows)} 筆資料回 {ACCOUNT_FILE}...")
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header_str + "\n")
        for row in final_output_rows:
            f.write(",".join(row) + "\n")
    print(f"[*] 處理完畢。現在可以啟動 Locust 進行測試。")


if __name__ == '__main__':
    process_integrated_tasks()