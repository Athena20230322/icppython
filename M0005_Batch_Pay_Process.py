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


# ==========================================
# 加密輔助工具 (保持穩定)
# ==========================================
class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        return {
            'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
            'public_key': key.publickey().export_key(format='PEM').decode('utf-8')
        }

    def import_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        cipher_rsa = PKCS1_v1_5.new(self._key)
        data_bytes = data.encode('utf-8')
        key_size = self._key.size_in_bytes()
        max_chunk = key_size - 11
        chunks = [data_bytes[i:i + max_chunk] for i in range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join([cipher_rsa.encrypt(c) for c in chunks])).decode('utf-8')

    def decrypt(self, enc_data):
        try:
            cipher_rsa = PKCS1_v1_5.new(self._key)
            enc_bytes = base64.b64decode(enc_data)
            key_size = self._key.size_in_bytes()
            chunks = [enc_bytes[i:i + key_size] for i in range(0, len(enc_bytes), key_size)]
            return b''.join([cipher_rsa.decrypt(c, b'error') for c in chunks]).decode('utf-8')
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


# ==========================================
# 核心 API 批次執行類別
# ==========================================
class IcashPayBatchFullProcess:
    def __init__(self):
        self.member_url = "https://icp-member-stage.icashpay.com.tw/"
        self.pay_url = "https://icp-payment-stage.icashpay.com.tw/"
        self.csv_path = "C:\\icppython\\account.csv"
        self.session = None

    def _get_ts(self):
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def _safe_api_call(self, response_json, decrypt_func):
        if 'EncData' not in response_json:
            msg = response_json.get('RtnMsg', '未知錯誤')
            code = response_json.get('RtnCode', '無代碼')
            return False, f"API 失敗 [{code}]: {msg}"
        dec = decrypt_func(response_json['EncData'])
        if not dec: return False, "解密內容為空"
        try:
            return True, json.loads(dec)
        except:
            return False, f"JSON 錯誤: {dec[:30]}"

    def _init_security(self):
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
                                     data={'EncData': enc_exch},
                                     headers={'X-iCP-DefaultPubCertID': str(def_id),
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
        return aes_final, kp['private_key']

    def start_process(self):
        print(f"[{datetime.now()}] 批次條碼作業開始...")
        df = pd.read_csv(self.csv_path, dtype=str, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        df['CellPhone'] = df['CellPhone'].apply(lambda x: '0' + str(x) if len(str(x)) == 9 else str(x))

        for i in range(len(df)):
            user_code = df.at[i, 'UserCode']
            phone = df.at[i, 'CellPhone']
            print(f"\n>>> 帳號: {user_code} ({phone})")

            for attempt in range(3):  # 外層重試：針對 10000 錯誤重新執行整個握手
                self.session = requests.Session()
                try:
                    # [A] 重新握手
                    aes_info, client_priv = self._init_security()
                    aes_tool = AesCryptoHelper(aes_info['AES_Key'], aes_info['AES_IV'])
                    rsa_tool = RsaCryptoHelper()
                    rsa_tool.import_key(client_priv)
                    key_id = str(aes_info['EncKeyID'])

                    # [B] Refresh Token
                    p_tk = {'Timestamp': self._get_ts(), 'CellPhone': phone}
                    enc_tk = aes_tool.encrypt(json.dumps(p_tk))
                    res_tk = self.session.post(f"{self.member_url}app/MemberInfo/RefreshLoginToken",
                                               data={'EncData': enc_tk},
                                               headers={'X-iCP-EncKeyID': key_id,
                                                        'X-iCP-Signature': rsa_tool.sign(enc_tk)}).json()
                    success, tk_data = self._safe_api_call(res_tk, aes_tool.decrypt)

                    if not success:
                        if "10000" in str(tk_data):
                            print(f"   ⚠️ 伺服器同步中，重新握手重試... ({attempt + 1}/3)")
                            time.sleep(3)  # 拉長等待
                            continue  # 跳出本次 attempt，重新 _init_security
                        else:
                            raise ValueError(tk_data)

                    tk_val = tk_data.get("LoginTokenID", "").split(',')[0]
                    df.at[i, 'LoginTokenID'] = tk_val

                    # [C] SMS
                    p_sms = {"Timestamp": self._get_ts(), "CellPhone": phone, "SMSAuthType": 5, "UserCode": "",
                             "LoginTokenID": tk_val}
                    enc_sms = aes_tool.encrypt(json.dumps(p_sms))
                    res_sms = self.session.post(f"{self.member_url}app/MemberInfo/SendAuthSMS",
                                                data={'EncData': enc_sms},
                                                headers={'X-iCP-EncKeyID': key_id,
                                                         'X-iCP-Signature': rsa_tool.sign(enc_sms)}).json()
                    success, sms_data = self._safe_api_call(res_sms, aes_tool.decrypt)
                    if not success: raise ValueError(sms_data)
                    auth_code = sms_data.get("AuthCode")
                    df.at[i, 'authcode'] = auth_code

                    # [D] Login
                    p_login = {"Timestamp": self._get_ts(), "LoginType": "1", "UserCode": user_code,
                               "UserPwd": "Aa123456", "SMSAuthCode": auth_code}
                    enc_login = aes_tool.encrypt(json.dumps(p_login))
                    res_login = self.session.post(f"{self.member_url}app/MemberInfo/UserCodeLogin2022",
                                                  data={'EncData': enc_login},
                                                  headers={'X-iCP-EncKeyID': key_id,
                                                           'X-iCP-Signature': rsa_tool.sign(enc_login)}).json()
                    self._safe_api_call(res_login, aes_tool.decrypt)

                    # [E] PayID & Barcode
                    p_p2 = {"Timestamp": self._get_ts(), "IsAutoPay": "false", "MerchantID": ""}
                    enc_p2 = aes_tool.encrypt(json.dumps(p_p2))
                    res_p2 = self.session.post(f"{self.pay_url}app/Payment/GetMemberPaymentInfo",
                                               data={'EncData': enc_p2},
                                               headers={'X-iCP-EncKeyID': key_id,
                                                        'X-iCP-Signature': rsa_tool.sign(enc_p2)}).json()
                    _, p2_data = self._safe_api_call(res_p2, aes_tool.decrypt)
                    pay_id = p2_data.get("AllIcashpayList", {}).get("PayID") or p2_data.get("IcashpayList", {}).get(
                        "PayID")

                    p_p1 = {"PayID": pay_id, "PaymentType": "1", "Timestamp": self._get_ts()}
                    enc_p1 = aes_tool.encrypt(json.dumps(p_p1))
                    res_p1 = self.session.post(f"{self.pay_url}app/Payment/CreateBarcode",
                                               data={'EncData': enc_p1},
                                               headers={'X-iCP-EncKeyID': key_id,
                                                        'X-iCP-Signature': rsa_tool.sign(enc_p1)}).json()
                    _, p1_data = self._safe_api_call(res_p1, aes_tool.decrypt)
                    barcode = p1_data.get("Barcode")

                    df.at[i, 'Barcode'] = barcode
                    df.to_csv(self.csv_path, index=False, encoding='utf-8-sig')
                    print(f"   ✅ 完成: {barcode}")
                    break  # 執行成功，跳出 attempt 迴圈

                except Exception as e:
                    if attempt == 2:  # 最後一次重試也失敗
                        print(f"   ❌ 最終失敗: {str(e)}")

            time.sleep(1)  # 帳號間間隔


if __name__ == '__main__':
    IcashPayBatchFullProcess().start_process()