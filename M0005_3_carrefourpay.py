import requests
import json
import base64
import os
import re
from datetime import datetime, timedelta
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# 設定路徑
SESSION_FILE = r"C:\icppython\session_cache.json"
BARCODE_FILE = r"C:\icppython\barcode.txt"
POST_DATA_DIR = r"C:\icppython\OpostData"
AUTH_CODE_FILE = r"C:\icppython\authcode.txt"
USERCODE_FILE = r"C:\icppython\usercode.txt"


class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        return {
            'private_key': key.export_key(format='PEM', pkcs=8).decode('utf-8'),
            'public_key': key.publickey().export_key(format='PEM').decode('utf-8')
        }

    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key):
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        key_size_bytes = self._key.size_in_bytes()
        max_chunk_size = key_size_bytes - 11
        data_bytes = data.encode('utf-8')
        encrypted_chunks = []
        for i in range(0, len(data_bytes), max_chunk_size):
            chunk = data_bytes[i:i + max_chunk_size]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            encrypted_chunks.append(cipher_rsa.encrypt(chunk))
        return base64.b64encode(b''.join(encrypted_chunks)).decode('utf-8')

    def decrypt(self, enc_data):
        try:
            encrypted_bytes = base64.b64decode(enc_data)
            key_size_bytes = self._key.size_in_bytes()
            decrypted_chunks = []
            for i in range(0, len(encrypted_bytes), key_size_bytes):
                chunk = encrypted_bytes[i:i + key_size_bytes]
                cipher_rsa = PKCS1_v1_5.new(self._key)
                decrypted_chunks.append(cipher_rsa.decrypt(chunk, b'error_sentinel'))
            return b''.join(decrypted_chunks).decode('utf-8')
        except:
            return None

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._key).sign(h)
        return base64.b64encode(signature).decode('utf-8')


class AesCryptoHelper:
    def __init__(self, key, iv):
        self.key = key.encode('utf-8') if isinstance(key, str) else key
        self.iv = iv.encode('utf-8') if isinstance(iv, str) else iv

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

    def decrypt(self, enc_data):
        try:
            encrypted_bytes = base64.b64decode(enc_data)
            cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
            decrypted = cipher.decrypt(encrypted_bytes)
            text = unpad(decrypted, AES.block_size, style='pkcs7').decode('utf-8').strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)
            return match.group() if match else text
        except:
            return None


class CertificateApiClient:
    def __init__(self, member_base_url="https://icp-member-preprod.icashpay.com.tw/",
                 payment_base_url="https://icp-payment-preprod.icashpay.com.tw/"):
        self.member_base_url = member_base_url
        self.payment_base_url = payment_base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._aes_key = None
        self._aes_iv = None
        self._aes_client_cert_id = -1
        self._client_private_key = None
        self._token = None

    def _read_config(self, filepath, default):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return content if content else default
        return default

    def save_session(self):
        session_data = {
            "client_private_key": self._client_private_key,
            "aes_key": self._aes_key,
            "aes_iv": self._aes_iv,
            "aes_cert_id": self._aes_client_cert_id,
            "token": self._token
        }
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)

        # --- 修改點：輸出金鑰資訊，讓總控程式能夠擷取並解密 ---
        key_info = {
            "AES_Key": self._aes_key,
            "AES_IV": self._aes_iv,
            "EncKeyID": self._aes_client_cert_id
        }
        print(f"AES_KEY_INFO:{json.dumps(key_info)}")
        # ---------------------------------------------------

    def generate_aes(self):
        resp = self.session.post(f"{self.member_base_url}api/member/Certificate/GetDefaultPucCert")
        def_data = resp.json()
        def_id, def_pub = def_data['DefaultPubCertID'], def_data['DefaultPubCert']

        kp = self.rsa_helper.generate_pem_key()
        self._client_private_key = kp['private_key']
        client_pub_oneline = "".join(kp['public_key'].splitlines()[1:-1])
        ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        content, _ = self._call_certificate_api("api/member/Certificate/ExchangePucCert", def_id, def_pub,
                                                self._client_private_key,
                                                {'ClientPubCert': client_pub_oneline, 'Timestamp': ts},
                                                "X-iCP-DefaultPubCertID")

        dec_exch = self.rsa_helper.decrypt(json.loads(content).get('EncData', ''))
        if not dec_exch: raise Exception("RSA Exchange 密文解密失敗")
        exch_res = json.loads(dec_exch)

        ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        content, _ = self._call_certificate_api("api/member/Certificate/GenerateAES", exch_res['ServerPubCertID'],
                                                exch_res['ServerPubCert'], self._client_private_key, {'Timestamp': ts},
                                                "X-iCP-ServerPubCertID")

        dec_aes = self.rsa_helper.decrypt(json.loads(content).get('EncData', ''))
        if not dec_aes: raise Exception("AES Key 密文解密失敗")
        aes_res = json.loads(dec_aes)

        self._aes_client_cert_id, self._aes_key, self._aes_iv = aes_res['EncKeyID'], aes_res['AES_Key'], aes_res[
            'AES_IV']

    def _call_certificate_api(self, action, cert_id, server_pub, client_priv, payload, header_name):
        json_payload = json.dumps(payload, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(server_pub)
        enc_data = self.rsa_helper.encrypt(json_payload)
        self.rsa_helper.import_pem_private_key(client_priv)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        headers = {header_name: str(cert_id), 'X-iCP-Signature': signature}
        response = self.session.post(f"{self.member_base_url}{action}", data={'EncData': enc_data}, headers=headers)
        return response.text, response.headers.get('X-iCP-Signature')

    def _call_normal_api(self, base_url, action, payload, filename=None):
        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        enc_data = aes_helper.encrypt(json.dumps(payload, ensure_ascii=False))
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        if filename:
            os.makedirs(POST_DATA_DIR, exist_ok=True)
            with open(os.path.join(POST_DATA_DIR, filename), "w") as f:
                f.write(f"{self._aes_client_cert_id},{signature},{enc_data}")

        headers = {
            'X-iCP-EncKeyID': str(self._aes_client_cert_id),
            'X-iCP-Signature': signature
        }
        if self._token:
            headers['X-iCP-AccessToken'] = self._token

        url = f"{base_url.rstrip('/')}/{action.lstrip('/')}"
        response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        res_json = response.json()

        if "EncData" in res_json and isinstance(res_json["EncData"], str):
            decrypted_text = aes_helper.decrypt(res_json["EncData"])
            if decrypted_text:
                res_json["EncData"] = json.loads(decrypted_text)
        return res_json

    def login_process(self):
        self.generate_aes()
        with open(AUTH_CODE_FILE, 'r') as f:
            auth_code = f.read().strip()

        user_code = self._read_config(USERCODE_FILE, "randyjan005")

        payload = {
            "Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "LoginType": "1",
            "UserCode": user_code,
            "UserPwd": "Aa123456",
            "SMSAuthCode": auth_code
        }
        print(f"嘗試以帳號 [{user_code}] 登入...")
        res = self._call_normal_api(self.member_base_url, "app/MemberInfo/UserCodeLogin2022", payload)

        inner_data = res.get("EncData", {})
        if res.get("RtnCode") == 1 or inner_data.get("RtnCode") == 1:
            self._token = inner_data.get("Token")
            # --- 修改點：印出完整回應 JSON，以便總控程式擷取解密結果 ---
            print(f"登入成功，Token 已取得。回應內容: {json.dumps(res, ensure_ascii=False)}")
            self.save_session()
        else:
            print(f"登入失敗回應: {res}")
            raise Exception("登入失敗")

    def run_specified_requests(self):
        def get_ts():
            return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        captured_pay_id = None
        # P0002
        print("\n=== 執行: P0002_GetMemberPaymentInfo ===")
        p0002_res = self._call_normal_api(self.payment_base_url, "app/Payment/GetMemberPaymentInfo",
                                          {"Timestamp": get_ts(), "IsAutoPay": "false", "MerchantID": ""},
                                          "postData3.txt")

        inner_p2 = p0002_res.get("EncData", {})
        if p0002_res.get("RtnCode") == 1 or inner_p2.get("RtnCode") == 1:
            pay_list = inner_p2.get("AllIcashpayList", {}) or inner_p2.get("IcashpayList", {})
            captured_pay_id = pay_list.get("PayID")
            print(f"成功取得 PayID: {captured_pay_id}")
        else:
            print(f"P0002 請求失敗: {p0002_res}")

        # P0001
        if captured_pay_id:
            print(f"\n=== 執行: P0001_CreateBarcode (PayID: {captured_pay_id}) ===")
            p0001_payload = {"PayID": captured_pay_id, "PaymentType": "1", "Timestamp": get_ts()}
            p0001_res = self._call_normal_api(self.payment_base_url, "app/Payment/CreateBarcode", p0001_payload,
                                              "postData12.txt")

            inner_p1 = p0001_res.get("EncData", {})
            if p0001_res.get("RtnCode") == 1 or inner_p1.get("RtnCode") == 1:
                barcode_val = inner_p1.get("Barcode")
                with open(BARCODE_FILE, "w") as f:
                    f.write(barcode_val)
                print(f"✅ Barcode 已儲存: {barcode_val}")
            else:
                print(f"P0001 請求失敗: {p0001_res}")
        else:
            print("\n❌ 無法取得 PayID，跳過 P0001")

        # M0132
        print("\n=== 執行: M0132_ChangeMemberPointSwitch (OFF) ===")
        m0132_res = self._call_normal_api(self.member_base_url, "app/MemberInfo/ChangeMemberPointSwitch",
                                          {"ChangeOpPointSwitch": False, "Timestamp": get_ts()},
                                          "postData_M0132_False.txt")
        print("M0132 執行完畢。")


if __name__ == '__main__':
    client = CertificateApiClient()
    try:
        print(f"系統時間: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
        client.login_process()
        client.run_specified_requests()
    except Exception as e:
        print(f"主程式錯誤: {e}")