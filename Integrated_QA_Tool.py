import requests
import json
import base64
import os
import re
import time
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# 設定路徑
ACCOUNT_FILE = "C:\\icppython\\account.txt"


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


def process_accounts():
    client = IcashPayClient()
    if not os.path.exists(ACCOUNT_FILE): return
    with open(ACCOUNT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if not lines: return

    # 修改標題增加 Count 欄位參考
    header = "UserCode,CellPhone,LoginTokenID,authcode,Barcode,Count"
    updated_rows = []

    for line in lines[1:]:
        if not line.strip(): continue
        acc = [p.strip() for p in line.split(',')]
        # 填充欄位確保至少有 6 個
        while len(acc) < 6: acc.append("")

        user_code, phone, current_token, current_auth, current_barcode, count_str = acc

        # 決定要產出幾次，預設為 1
        try:
            repeat_count = int(count_str) if count_str and int(count_str) > 0 else 1
        except ValueError:
            repeat_count = 1

        print(f"\n>>> 正在處理帳號: {phone} (預計產出 {repeat_count} 筆條碼)")

        try:
            client.handshake()
            # 1. Token
            res_token = client.call_api(client.member_url, "app/MemberInfo/RefreshLoginToken",
                                        {"Timestamp": client._get_timestamp(), "CellPhone": phone})
            new_token = res_token.get("EncData", {}).get("LoginTokenID", "").split(',')[0]

            # 2. SMS
            res_sms = client.call_api(client.member_url, "app/MemberInfo/SendAuthSMS",
                                      {"Timestamp": client._get_timestamp(), "CellPhone": phone,
                                       "SMSAuthType": 5, "UserCode": "", "LoginTokenID": new_token})
            new_auth = res_sms.get("EncData", {}).get("AuthCode", "")

            # 3. Login
            client.call_api(client.member_url, "app/MemberInfo/UserCodeLogin2022",
                            {"Timestamp": client._get_timestamp(), "LoginType": "1",
                             "UserCode": user_code, "UserPwd": "Aa123456", "SMSAuthCode": new_auth})

            time.sleep(1)

            # 4. PayID
            res_pay = client.call_api(client.payment_url, "app/Payment/GetMemberPaymentInfo",
                                      {"Timestamp": client._get_timestamp(), "IsAutoPay": "false", "MerchantID": ""})
            p_data = res_pay.get("EncData", {})
            pay_id = None
            for sk in ["AllIcashpayList", "IcashpayList", "PaymentList"]:
                target = p_data.get(sk)
                if not target: continue
                if isinstance(target, list) and len(target) > 0:
                    pay_id = target[0].get("PayID")
                elif isinstance(target, dict):
                    pay_id = target.get("PayID")
                if pay_id: break

            if pay_id:
                # 根據 repeat_count 產出多筆條碼
                for i in range(repeat_count):
                    res_bc = client.call_api(client.payment_url, "app/Payment/CreateBarcode",
                                             {"PayID": pay_id, "PaymentType": "1",
                                              "Timestamp": client._get_timestamp()})
                    new_barcode = res_bc.get("EncData", {}).get("Barcode", "")
                    print(f"   [# {i + 1}] 條碼: {new_barcode}")
                    # 將結果存入列表
                    updated_rows.append([user_code, phone, new_token, new_auth, new_barcode, str(repeat_count)])
                    # 避免連續請求過快
                    if repeat_count > 1: time.sleep(0.5)
            else:
                print(f"⚠️ 無法取得 PayID。回傳訊息: {res_pay.get('RtnMsg')}")
                updated_rows.append([user_code, phone, new_token, new_auth, "", str(repeat_count)])

        except Exception as e:
            print(f"❌ 帳號 {phone} 系統報錯: {e}")
            updated_rows.append([user_code, phone, current_token, current_auth, current_barcode, count_str])

    # 寫回檔案
    with open(ACCOUNT_FILE, 'w', encoding='utf-8') as f:
        f.write(header + "\n")
        for row in updated_rows:
            f.write(",".join(row) + "\n")
    print(f"\n處理完畢，account.txt 已更新，總共產生 {len(updated_rows)} 筆記錄。")


if __name__ == '__main__':
    process_accounts()