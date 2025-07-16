# C:\icppython\full_registration_flow.py (已整合 7 個 API 步驟)
import requests
import json
import base64
import os
import sys
from datetime import datetime
import random

# 確保 pycryptodome 已安裝
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5, AES
    from Crypto.Hash import SHA256
    from Crypto.Signature import pkcs1_15
    from Crypto.Util.Padding import pad, unpad
except ImportError:
    print("!!! 錯誤: 找不到 pycryptodome 模組。請執行 'pip install pycryptodome' 安裝。 !!!")
    sys.exit(1)

# --- 全域設定 ---
BASE_PATH = "C:\\icppython"
LAST_PHONE_FILE = os.path.join(BASE_PATH, "last_phone.txt")
LAST_IDNO_FILE = os.path.join(BASE_PATH, "last_idno.txt")
TOKEN_FILE = os.path.join(BASE_PATH, "reglogintokenid.txt")
AUTH_CODE_FILE = os.path.join(BASE_PATH, "regauthcode.txt")


# --- 共用函式 ---
def generate_taiwan_id():
    """產生一個隨機的中華民國身分證號碼。"""
    letter_map = {
        'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 34,
        'J': 18, 'K': 19, 'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23, 'Q': 24, 'R': 25,
        'S': 26, 'T': 27, 'U': 28, 'V': 29, 'W': 32, 'X': 30, 'Y': 31, 'Z': 33
    }
    city_letter = random.choice(list(letter_map.keys()))
    gender = random.choice([1, 2])
    middle_digits = [random.randint(0, 9) for _ in range(7)]
    p0 = letter_map[city_letter]
    all_digits_for_check = [p0 // 10, p0 % 10, gender] + middle_digits
    weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    total = sum(d * w for d, w in zip(all_digits_for_check, weights))
    checksum = (10 - (total % 10)) % 10
    return f"{city_letter}{gender}{''.join(map(str, middle_digits))}{checksum}"


def get_next_phone_number(start_number=950001617):
    """讀取檔案中的手機號碼，將其加一，然後寫回檔案。"""
    try:
        os.makedirs(os.path.dirname(LAST_PHONE_FILE), exist_ok=True)
        with open(LAST_PHONE_FILE, 'r') as f:
            next_number = int(f.read().strip()[1:]) + 1
    except (FileNotFoundError, ValueError):
        next_number = start_number
    phone_number = f"0{next_number}"
    with open(LAST_PHONE_FILE, 'w') as f:
        f.write(phone_number)
    return phone_number


# --- 加密/解密輔助類別 (合併版) ---
class RsaCryptoHelper:
    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        private_key_pem = key.export_key(format='PEM', pkcs=8).decode('utf-8')
        public_key_pem = key.publickey().export_key(format='PEM').decode('utf-8')
        return {'private_key': private_key_pem, 'public_key': public_key_pem}

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
        if b'error_sentinel' in decrypted_chunks:
            raise ValueError("RSA 解密失敗。")
        return b''.join(decrypted_chunks).decode('utf-8')

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        return base64.b64encode(pkcs1_15.new(self._key).sign(h)).decode('utf-8')

    def verify_sign_data_with_sha256(self, data, signature):
        h = SHA256.new(data.encode('utf-8'))
        if signature is None: return False
        try:
            pkcs1_15.new(self._key).verify(h, base64.b64decode(signature))
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
    def __init__(self, key, iv):
        self.key = key.encode('utf-8')
        self.iv = iv.encode('utf-8')

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        return base64.b64encode(cipher.encrypt(padded_data)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        return unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7').decode('utf-8')


# --- 主要 API 客戶端類別 ---
class FullFlowApiClient:
    def __init__(self, base_url="https://icp-member-stage.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key = None
        self._client_private_key = None
        self._aes_key_id = None
        self._aes_key = None
        self._aes_iv = None
        self._login_token_id = None

    def _call_api(self, endpoint, payload, use_aes=True, skip_verification=False):
        """通用 API 呼叫函式"""
        print(f"\n--- 步驟: 呼叫 {endpoint} ---")
        json_payload = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

        if use_aes:
            if not all([self._aes_key, self._aes_iv, self._aes_key_id]):
                raise Exception("AES 金鑰尚未初始化，無法進行 AES 加密通訊。")
            aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
            enc_data = aes_helper.encrypt(json_payload)
            headers = {'X-iCP-EncKeyID': str(self._aes_key_id)}
        else:
            self.rsa_helper.import_pem_public_key(payload['ServerPubKey'])
            enc_data = self.rsa_helper.encrypt(json_payload)
            headers = {'X-iCP-DefaultPubCertID': str(payload['CertID'])}

        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        headers['X-iCP-Signature'] = signature

        url = f"{self.base_url}{endpoint}"
        print(f"Request Payload (加密前): {json_payload}")
        response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        response.raise_for_status()

        response_content = response.text
        print(f"API 原始回應: {response_content}")
        response_signature = response.headers.get('X-iCP-Signature')

        if not skip_verification:
            self.rsa_helper.import_pem_public_key(self._server_public_key)
            if not self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature):
                raise Exception(f"{endpoint} 的回應簽章驗證失敗。")
            print("回應簽章驗證成功。")

        response_json = json.loads(response_content)
        if response_json.get('RtnCode') != 1:
            raise Exception(f"API 返回錯誤 (RtnCode {response_json.get('RtnCode')}): {response_json.get('RtnMsg')}")

        if use_aes:
            aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
            decrypted_data_str = aes_helper.decrypt(response_json['EncData'])
        else:
            self.rsa_helper.import_pem_private_key(self._client_private_key)
            decrypted_data_str = self.rsa_helper.decrypt(response_json['EncData'])

        print(f"回應 (已解密): {decrypted_data_str}")
        decrypted_json = json.loads(decrypted_data_str)

        return decrypted_json, response_content, response_signature

    def run_full_flow(self):
        """完整執行註冊到身分驗證的流程"""
        try:
            # === 準備階段：產生動態資料 ===
            user_code = f"i{int(datetime.now().timestamp())}"
            cell_phone = get_next_phone_number()
            id_no = generate_taiwan_id()
            with open(LAST_IDNO_FILE, 'w') as f:
                f.write(id_no)
            print(f"動態資料已產生: UserCode={user_code}, CellPhone={cell_phone}, IDNo={id_no}")

            # === 金鑰交換流程 ===
            self._initialize_keys()

            # === 步驟 1: 設定註冊資訊 (SetRegisterInfo2022) ===
            payload1 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'CellPhone': cell_phone,
                'UserCode': user_code,
                'UserPwd': 'Aa123456'
            }
            result1, _, _ = self._call_api("app/MemberInfo/SetRegisterInfo2022", payload1)
            self._login_token_id = result1.get("LoginTokenID")
            if not self._login_token_id:
                raise Exception("步驟 1 未能獲取 LoginTokenID。")
            with open(TOKEN_FILE, 'w') as f:
                f.write(self._login_token_id)
            print(f"LoginTokenID '{self._login_token_id}' 已儲存。")

            # === 步驟 2: 發送簡訊驗證碼 (SendAuthSMS) ===
            payload2 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'CellPhone': cell_phone,
                'LoginTokenID': self._login_token_id,
                'SMSAuthType': '1',
                'UserCode': ''
            }
            result2, _, _ = self._call_api("app/MemberInfo/SendAuthSMS", payload2)
            auth_code = result2.get("AuthCode")
            if not auth_code:
                raise Exception("步驟 2 未能獲取 AuthCode。")
            with open(AUTH_CODE_FILE, 'w') as f:
                f.write(auth_code)
            print(f"AuthCode '{auth_code}' 已儲存。")

            # === 步驟 3: 驗證簡訊 (CheckRegisterAuthSMS) ===
            payload3 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'CellPhone': cell_phone,
                'LoginTokenID': self._login_token_id,
                'AuthCode': auth_code
            }
            self._call_api("app/MemberInfo/CheckRegisterAuthSMS", payload3)
            print("簡訊驗證成功。")

            # === 步驟 4: 身分驗證 (AuthIDNO) ===
            payload4 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'LoginTokenID': self._login_token_id,
                "Address": "板橋區中山路一段161號",
                "AreaID": "220",
                "BirthDay": "2000-01-01",
                "CName": "測試一",
                "Email": f"{user_code}@test.com",
                "Idno": id_no,
                "IssueDate": "2020-01-01",
                "IssueLoc": "65000",
                "IssueType": "1",
                "NationalityID": "1206",
                "fileCols": "img1,img2"
            }
            self._call_api("app/MemberInfo/AuthIDNO", payload4)
            print("身分驗證成功。")

            ### ### 新增步驟 5/6/7 ### ###

            # === 步驟 5: 變更交易密碼 (ChangeSecurityPwd) ===
            payload5 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'ConfirmSecPwd': "246790",
                'NewSecPwd': "246790"
            }
            self._call_api("app/MemberInfo/ChangeSecurityPwd", payload5)
            print("變更交易密碼成功。")

            # === 步驟 6: 檢查是否為OP會員 (CheckIsOP) ===
            payload6 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'CellPhone': cell_phone
            }
            self._call_api("app/MemberInfo/CheckIsOP", payload6)
            print("檢查OP會員狀態成功。")

            # === 步驟 7: 註冊為OP會員 (RegisterOpMember) ===
            payload7 = {
                'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                'CellPhone': cell_phone,
                'Birthday': "20000101"
            }
            self._call_api("app/MemberInfo/RegisterOpMember", payload7)
            print("註冊OP會員成功。")

            print("\n======= ✅ 全部 7 個步驟流程執行成功！ ✅ =======")

        except Exception as e:
            print(f"\n======= ❌ 流程執行失敗 ❌ =======")
            print(f"錯誤訊息: {e}")
            import traceback
            traceback.print_exc()
            print(f"====================================")

    def _initialize_keys(self):
        """處理 GetDefaultPucCert, ExchangePucCert, 和 GenerateAES 的完整流程"""
        print("--- 階段: 初始化金鑰 ---")
        # 1. GetDefaultPucCert
        url1 = f"{self.base_url}api/member/Certificate/GetDefaultPucCert"
        response1 = self.session.post(url1).json()
        if response1['RtnCode'] != 1: raise Exception("GetDefaultPucCert 失敗")
        default_cert_id = response1['DefaultPubCertID']
        default_public_key = response1['DefaultPubCert']
        self._server_public_key = default_public_key

        # 2. ExchangePucCert
        client_keys = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_keys['private_key']
        client_pub_oneline = "".join(client_keys['public_key'].splitlines()[1:-1])

        payload2 = {
            'ClientPubCert': client_pub_oneline,
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CertID': default_cert_id,
            'ServerPubKey': default_public_key
        }
        decrypted_result, raw_content, signature = self._call_api(
            "api/member/Certificate/ExchangePucCert", payload2, use_aes=False, skip_verification=True
        )

        self._server_public_key = decrypted_result['ServerPubCert']
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(raw_content, signature):
            raise Exception("ExchangePucCert 回應的手動簽章驗證失敗。")
        print("ExchangePucCert 回應手動簽章驗證成功。")
        server_pub_cert_id = decrypted_result['ServerPubCertID']

        # 3. GenerateAES
        payload3 = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        json_payload3 = json.dumps(payload3, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        enc_data3 = self.rsa_helper.encrypt(json_payload3)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature3 = self.rsa_helper.sign_data_with_sha256(enc_data3)
        headers3 = {
            'X-iCP-ServerPubCertID': str(server_pub_cert_id),
            'X-iCP-Signature': signature3
        }
        url3 = f"{self.base_url}api/member/Certificate/GenerateAES"
        response3 = self.session.post(url3, data={'EncData': enc_data3}, headers=headers3)
        response3.raise_for_status()

        content3 = response3.text
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(content3, response3.headers.get('X-iCP-Signature')):
            raise Exception("GenerateAES 簽章驗證失敗")

        result3_enc = json.loads(content3)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        result3_dec = json.loads(self.rsa_helper.decrypt(result3_enc['EncData']))

        self._aes_key_id = result3_dec['EncKeyID']
        self._aes_key = result3_dec['AES_Key']
        self._aes_iv = result3_dec['AES_IV']
        print(f"金鑰初始化成功，AES KeyID: {self._aes_key_id}")


if __name__ == '__main__':
    api_client = FullFlowApiClient()
    api_client.run_full_flow()