import requests
import json
import base64
import os
import re
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# 設定路徑
SESSION_FILE = "C:\\icppython\\session_cache.json"
BARCODE_FILE = "C:\\icppython\\barcode.txt"
POST_DATA_DIR = "C:\\icppython\\OpostData"
# ================= 修改點 1: 新增帳號配置檔案路徑 =================
CONFIG_FILE = "C:\\icppython\\current_user.json"


# =============================================================


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
        encrypted_bytes = base64.b64decode(enc_data)
        key_size_bytes = self._key.size_in_bytes()
        decrypted_chunks = []
        for i in range(0, len(encrypted_bytes), key_size_bytes):
            chunk = encrypted_bytes[i:i + key_size_bytes]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            decrypted_chunks.append(cipher_rsa.decrypt(chunk, b'error_sentinel'))
        return b''.join(decrypted_chunks).decode('utf-8')

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
        except Exception:
            return None


class CertificateApiClient:
    def __init__(self, member_base_url="https://icp-member-stage.icashpay.com.tw/",
                 payment_base_url="https://icp-payment-stage.icashpay.com.tw/"):
        self.member_base_url = member_base_url
        self.payment_base_url = payment_base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._aes_key = None
        self._aes_iv = None
        self._aes_client_cert_id = -1
        self._client_private_key = None

    def save_session(self):
        session_data = {
            "client_private_key": self._client_private_key,
            "aes_key": self._aes_key,
            "aes_iv": self._aes_iv,
            "aes_cert_id": self._aes_client_cert_id
        }
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(session_data, f)

    def load_session(self):
        if os.path.exists(SESSION_FILE):
            try:
                with open(SESSION_FILE, 'r') as f:
                    data = json.load(f)
                    self._client_private_key = data["client_private_key"]
                    self._aes_key = data["aes_key"]
                    self._aes_iv = data["aes_iv"]
                    self._aes_client_cert_id = data["aes_cert_id"]
                return True
            except:
                return False
        return False

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
        exch_res = json.loads(self.rsa_helper.decrypt(json.loads(content)['EncData']))
        ts = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        content, _ = self._call_certificate_api("api/member/Certificate/GenerateAES", exch_res['ServerPubCertID'],
                                                exch_res['ServerPubCert'], self._client_private_key, {'Timestamp': ts},
                                                "X-iCP-ServerPubCertID")
        aes_res = json.loads(self.rsa_helper.decrypt(json.loads(content)['EncData']))
        self._aes_client_cert_id, self._aes_key, self._aes_iv = aes_res['EncKeyID'], aes_res['AES_Key'], aes_res[
            'AES_IV']
        print(f"AES_KEY_INFO:{json.dumps(aes_res)}")

    def _call_certificate_api(self, action, cert_id, server_pub, client_priv, payload, header_name):
        json_payload = json.dumps(payload, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(server_pub)
        enc_data = self.rsa_helper.encrypt(json_payload)
        self.rsa_helper.import_pem_private_key(client_priv)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        headers = {header_name: str(cert_id), 'X-iCP-Signature': signature}
        url = f"{self.member_base_url}{action}"
        response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
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

        headers = {'X-iCP-EncKeyID': str(self._aes_client_cert_id), 'X-iCP-Signature': signature}
        url = f"{base_url.rstrip('/')}/{action.lstrip('/')}"

        try:
            response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
            res_json = response.json()
            if "EncData" in res_json and isinstance(res_json["EncData"], str):
                decrypted_text = aes_helper.decrypt(res_json["EncData"])
                if decrypted_text:
                    try:
                        res_json["EncData"] = json.loads(decrypted_text)
                    except:
                        pass
            return res_json
        except Exception as e:
            print(f"API 呼叫失敗: {e}")
            return None

    # ================= 修改點 2: login_process 改為讀取配置檔案 =================
    def login_process(self):
        self.generate_aes()

        # 讀取當前切換的帳號資料
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    user_info = json.load(f)
            else:
                # 預設後備值
                user_info = {"UserCode": "i1753422584", "CellPhone": "0950001657"}
        except Exception as e:
            print(f"讀取帳號配置失敗，使用預設值。錯誤: {e}")
            user_info = {"UserCode": "i1753422584", "CellPhone": "0950001657"}

        print(f"正在執行登入，帳號 (UserCode): {user_info['UserCode']}")

        with open("C:\\icppython\\authcode.txt", 'r') as f:
            auth_code = f.read().strip()

        payload = {
            "Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "LoginType": "1",
            "UserCode": user_info['UserCode'],  # 從原本寫死的 "i1753422584" 改為變數
            "UserPwd": "Aa123456",
            "SMSAuthCode": auth_code
        }

        res = self._call_normal_api(self.member_base_url, "app/MemberInfo/UserCodeLogin2022", payload)
        if isinstance(res, dict) and (res.get("RtnCode") == 1 or "EncData" in res):
            print("✅ 登入成功")
            self.save_session()
        else:
            raise Exception(f"❌ 登入失敗: {res}")

    # =============================================================================

    def run_specified_requests(self):
        def get_ts():
            return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

        captured_pay_id = None
        # P0002
        print("\n=== 執行: P0002_GetMemberPaymentInfo ===")
        p0002_res = self._call_normal_api(self.payment_base_url, "app/Payment/GetMemberPaymentInfo",
                                          {"Timestamp": get_ts(), "IsAutoPay": "false", "MerchantID": ""},
                                          "postData3.txt")

        if isinstance(p0002_res, dict) and "EncData" in p0002_res:
            inner_data = p0002_res["EncData"]
            captured_pay_id = inner_data.get("AllIcashpayList", {}).get("PayID") or \
                              inner_data.get("IcashpayList", {}).get("PayID")

        # P0001
        if captured_pay_id:
            print(f"\n=== 執行: P0001_CreateBarcode (PayID: {captured_pay_id}) ===")
            p0001_payload = {"PayID": captured_pay_id, "PaymentType": "1", "Timestamp": get_ts()}
            p0001_res = self._call_normal_api(self.payment_base_url, "app/Payment/CreateBarcode", p0001_payload,
                                              "postData12.txt")
            print(f"P0001 API 回應 (已解密):\n{json.dumps(p0001_res, indent=4, ensure_ascii=False)}")
            if isinstance(p0001_res, dict) and "EncData" in p0001_res:
                barcode_val = p0001_res["EncData"].get("Barcode")
                if barcode_val:
                    with open(BARCODE_FILE, "w") as f:
                        f.write(barcode_val)
                    print(f"✅ Barcode 已儲存: {barcode_val}")
        else:
            print("\n❌ 無法取得 PayID，跳過 P0001")

        # M0132
        print("\n=== 執行: M0132_ChangeMemberPointSwitch (OFF) ===")
        m0132_payload = {
            "ChangeOpPointSwitch": False,
            "Timestamp": get_ts()
        }
        m0132_res = self._call_normal_api(self.member_base_url, "app/MemberInfo/ChangeMemberPointSwitch", m0132_payload,
                                          "postData_M0132_False.txt")
        print(f"M0132 API 回應 (已解密):\n{json.dumps(m0132_res, indent=4, ensure_ascii=False)}")


if __name__ == '__main__':
    client = CertificateApiClient()
    try:
        print(f"系統時間: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
        client.login_process()
        client.run_specified_requests()
    except Exception as e:
        print(f"主程式錯誤: {e}")