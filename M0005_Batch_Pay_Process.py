import requests
import json
import base64
import os
import pandas as pd
import time
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# === 加密工具類別 (保持不變) ===
class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        return {'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
                'public_key': key.publickey().export_key(format='PEM').decode('utf-8')}

    def import_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        cipher = PKCS1_v1_5.new(self._key)
        data_bytes = data.encode('utf-8')
        max_chunk = self._key.size_in_bytes() - 11
        chunks = [data_bytes[i:i + max_chunk] for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join([cipher.encrypt(c) for c in chunks])).decode('utf-8')

    def decrypt(self, enc_data):
        try:
            cipher = PKCS1_v1_5.new(self._key)
            enc_bytes = base64.b64decode(enc_data)
            chunks = [enc_bytes[i:i + self._key.size_in_bytes()] for i in
                      range(0, len(enc_bytes), self._key.size_in_bytes())]
            return b''.join([cipher.decrypt(c, b'error') for c in chunks]).decode('utf-8')
        except:
            return ""

    def sign(self, data):
        h = SHA256.new(data.encode('utf-8'))
        return base64.b64encode(pkcs1_15.new(self._key).sign(h)).decode('utf-8')


class AesCryptoHelper:
    def __init__(self, key, iv):
        self.key = key.encode('utf-8') if isinstance(key, str) else key
        self.iv = iv.encode('utf-8') if isinstance(iv, str) else iv

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return base64.b64encode(cipher.encrypt(pad(data.encode('utf-8'), 16))).decode('utf-8')

    def decrypt(self, enc_data):
        try:
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            return unpad(cipher.decrypt(base64.b64decode(enc_data)), 16).decode('utf-8')
        except:
            return ""


class IcashPayBatchFullProcess:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.pay_url = "https://icp-payment-stage.icashpay.com.tw/"
        self.csv_path = "C:\\icppython\\account.csv"
        self.session = None

    def _get_ts(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def _safe_api_call(self, response_json, decrypt_func):
        if not isinstance(response_json, dict) or 'EncData' not in response_json:
            msg = response_json.get('RtnMsg', '未知錯誤') if isinstance(response_json, dict) else "非JSON回應"
            return False, msg
        dec = decrypt_func(response_json['EncData'])
        if not dec: return False, "解密失敗"
        return True, json.loads(dec)

    def _init_security(self):
        # 每次握手都重新初始化
        rsa_tool = RsaCryptoHelper()
        resp = self.session.post(f"{self.member_url}api/member/Certificate/GetDefaultPucCert").json()
        def_id, def_pub = resp['DefaultPubCertID'], resp['DefaultPubCert']
        kp = rsa_tool.generate_pem_key()
        pub_oneline = "".join(kp['public_key'].splitlines()[1:-1])
        rsa_tool.import_key(def_pub)
        enc_exch = rsa_tool.encrypt(json.dumps({'ClientPubCert': pub_oneline, 'Timestamp': self._get_ts()}))
        rsa_tool.import_key(kp['private_key'])
        sig_exch = rsa_tool.sign(enc_exch)
        res_exch = self.session.post(f"{self.member_url}api/member/Certificate/ExchangePucCert",
                                     data={'EncData': enc_exch}, headers={'X-iCP-DefaultPubCertID': str(def_id),
                                                                          'X-iCP-Signature': sig_exch}).json()
        success, exch_data = self._safe_api_call(res_exch, rsa_tool.decrypt)
        if not success: raise ValueError(exch_data)

        rsa_tool.import_key(exch_data['ServerPubCert'])
        enc_aes = rsa_tool.encrypt(json.dumps({'Timestamp': self._get_ts()}))
        rsa_tool.import_key(kp['private_key'])
        sig_aes = rsa_tool.sign(enc_aes)
        res_aes = self.session.post(f"{self.member_url}api/member/Certificate/GenerateAES",
                                    data={'EncData': enc_aes},
                                    headers={'X-iCP-ServerPubCertID': str(exch_data['ServerPubCertID']),
                                             'X-iCP-Signature': sig_aes}).json()
        success, aes_final = self._safe_api_call(res_aes, rsa_tool.decrypt)
        if not success: raise ValueError(aes_final)

        # *** 核心修正：握手完強制等待 5 秒，確保環境金鑰同步 ***
        print("   ⏳ 金鑰握手完成，強制等待伺服器同步 5 秒...")
        time.sleep(5)
        return aes_final, kp['private_key']

    def start_process(self):
        print(f"[{datetime.now()}] 批次自動化啟動...")
        df = pd.read_csv(self.csv_path, dtype=str, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        df['CellPhone'] = df['CellPhone'].apply(lambda x: '0' + str(x) if len(str(x)) == 9 else str(x))

        for i in range(len(df)):
            user_code, phone = df.at[i, 'UserCode'], df.at[i, 'CellPhone']
            print(f"\n>>> 執行: {user_code}")

            self.session = requests.Session()  # 清空連線與 Session
            try:
                aes_info, client_priv = self._init_security()
                aes_tool = AesCryptoHelper(aes_info['AES_Key'], aes_info['AES_IV'])
                rsa_tool = RsaCryptoHelper()
                rsa_tool.import_key(client_priv)
                key_id = str(aes_info['EncKeyID'])

                # 1. Refresh Token
                p_tk = {'Timestamp': self._get_ts(), 'CellPhone': phone}
                enc_tk = aes_tool.encrypt(json.dumps(p_tk))
                res_tk = self.session.post(f"{self.member_url}app/MemberInfo/RefreshLoginToken",
                                           data={'EncData': enc_tk}, headers={'X-iCP-EncKeyID': key_id,
                                                                              'X-iCP-Signature': rsa_tool.sign(
                                                                                  enc_tk)}).json()
                success, tk_data = self._safe_api_call(res_tk, aes_tool.decrypt)

                if not success: raise ValueError(tk_data)

                tk_val = tk_data.get("LoginTokenID", "").split(',')[0]
                df.at[i, 'LoginTokenID'] = tk_val

                # 2. SMS (直接取 AuthCode)
                p_sms = {"Timestamp": self._get_ts(), "CellPhone": phone, "SMSAuthType": 5, "UserCode": "",
                         "LoginTokenID": tk_val}
                enc_sms = aes_tool.encrypt(json.dumps(p_sms))
                res_sms = self.session.post(f"{self.member_url}app/MemberInfo/SendAuthSMS",
                                            data={'EncData': enc_sms}, headers={'X-iCP-EncKeyID': key_id,
                                                                                'X-iCP-Signature': rsa_tool.sign(
                                                                                    enc_sms)}).json()
                _, sms_data = self._safe_api_call(res_sms, aes_tool.decrypt)
                auth_code = sms_data.get("AuthCode")
                df.at[i, 'authcode'] = auth_code

                # 3. Login
                p_login = {"Timestamp": self._get_ts(), "LoginType": "1", "UserCode": user_code, "UserPwd": "Aa123456",
                           "SMSAuthCode": auth_code}
                enc_login = aes_tool.encrypt(json.dumps(p_login))
                self.session.post(f"{self.member_url}app/MemberInfo/UserCodeLogin2022",
                                  data={'EncData': enc_login},
                                  headers={'X-iCP-EncKeyID': key_id, 'X-iCP-Signature': rsa_tool.sign(enc_login)})

                # 4. Barcode
                p_p2 = {"Timestamp": self._get_ts(), "IsAutoPay": "false", "MerchantID": ""}
                enc_p2 = aes_tool.encrypt(json.dumps(p_p2))
                res_p2 = self.session.post(f"{self.pay_url}app/Payment/GetMemberPaymentInfo",
                                           data={'EncData': enc_p2}, headers={'X-iCP-EncKeyID': key_id,
                                                                              'X-iCP-Signature': rsa_tool.sign(
                                                                                  enc_p2)}).json()
                _, p2_data = self._safe_api_call(res_p2, aes_tool.decrypt)
                pay_id = p2_data.get("AllIcashpayList", {}).get("PayID") or p2_data.get("IcashpayList", {}).get("PayID")

                p_p1 = {"PayID": pay_id, "PaymentType": "1", "Timestamp": self._get_ts()}
                enc_p1 = aes_tool.encrypt(json.dumps(p_p1))
                res_p1 = self.session.post(f"{self.pay_url}app/Payment/CreateBarcode",
                                           data={'EncData': enc_p1}, headers={'X-iCP-EncKeyID': key_id,
                                                                              'X-iCP-Signature': rsa_tool.sign(
                                                                                  enc_p1)}).json()
                _, p1_data = self._safe_api_call(res_p1, aes_tool.decrypt)
                barcode = p1_data.get("Barcode")

                df.at[i, 'Barcode'] = barcode
                df.to_csv(self.csv_path, index=False, encoding='utf-8-sig')
                print(f"   ✅ 條碼: {barcode}")

            except Exception as e:
                print(f"   ❌ 錯誤: {str(e)}")
            time.sleep(1)

        print("\n任務結束。")


if __name__ == '__main__':
    IcashPayBatchFullProcess().start_process()