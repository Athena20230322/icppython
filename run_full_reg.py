import requests
import json
import base64
import os
from datetime import datetime
import random
import time

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


def generate_taiwan_id():
    """
    產生一個隨機的中華民國身分證號碼。
    """
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

    id_number = f"{city_letter}{gender}{''.join(map(str, middle_digits))}{checksum}"
    return id_number


class RsaCryptoHelper:
    """
    用於 RSA 加密、解密、簽章和驗證的輔助類別。
    """

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
        try:
            encrypted_bytes = base64.b64decode(enc_data)
            key_size_bytes = self._key.size_in_bytes()
            decrypted_chunks = []
            for i in range(0, len(encrypted_bytes), key_size_bytes):
                chunk = encrypted_bytes[i:i + key_size_bytes]
                cipher_rsa = PKCS1_v1_5.new(self._key)
                decrypted_chunks.append(cipher_rsa.decrypt(chunk, b'error_sentinel'))
            if b'error_sentinel' in decrypted_chunks:
                raise ValueError("解密過程中至少有一個區塊失敗。")
            return b''.join(decrypted_chunks).decode('utf-8')
        except Exception as e:
            raise ValueError(f"解密失敗，請確認 RSA 金鑰或資料是否正確。內部錯誤: {e}")

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._key).sign(h)
        return base64.b64encode(signature).decode('utf-8')

    def verify_sign_data_with_sha256(self, data, signature):
        h = SHA256.new(data.encode('utf-8'))
        if signature is None: return False
        signature_bytes = base64.b64decode(signature)
        try:
            pkcs1_15.new(self._key).verify(h, signature_bytes)
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
    """
    用於 AES 加密和解密 (CBC 模式) 的輔助類別。
    """

    def __init__(self, key=None, iv=None):
        self.key = key.encode('utf-8') if key else None
        self.iv = iv.encode('utf-8') if iv else None

    def encrypt(self, data):
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        encrypted_bytes = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        unpadded_bytes = unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7')
        return unpadded_bytes.decode('utf-8')


class FullRegistrationFlow:
    """
    將所有註冊步驟整合在一個類別中，以維持同一個連線狀態。
    """

    def __init__(self, base_url="https://icp-member-stage.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key = None
        self._client_public_key = None
        self._client_private_key = None
        self._aes_client_cert_id = -1
        self._aes_key = None
        self._aes_iv = None
        # 用於在步驟間傳遞狀態的變數
        self.login_token_id = None
        self.auth_code = None
        self.dynamic_cellphone = None
        self.dynamic_idno = None
        self.dynamic_user_code = None

    def _call_api(self, action, payload, is_cert_api=False, cert_header_name=None, cert_id=None, verification_key=None):
        """
        統一的 API 呼叫方法，處理加密、簽章和解密。
        """
        encryption_key = self._server_public_key
        if verification_key is None:
            verification_key = encryption_key

        # 【修正】統一所有 JSON 序列化格式，移除多餘空格
        json_payload = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

        if is_cert_api:
            self.rsa_helper.import_pem_public_key(encryption_key)
            enc_data = self.rsa_helper.encrypt(json_payload)
            self.rsa_helper.import_pem_private_key(self._client_private_key)
            signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        else:  # Normal API Call
            aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
            enc_data = aes_helper.encrypt(json_payload)
            self.rsa_helper.import_pem_private_key(self._client_private_key)
            signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        form_data = {'EncData': enc_data}
        headers = {'X-iCP-Signature': signature}
        if is_cert_api:
            headers[cert_header_name] = str(cert_id)
        else:
            headers['X-iCP-EncKeyID'] = str(self._aes_client_cert_id)

        url = f"{self.base_url}{action}"
        print(f"--- 呼叫 API: {url} ---")
        print(
            f"--- 請求 Payload (加密前) ---\n{json.dumps(payload, ensure_ascii=False, indent=4)}\n--------------------")

        response = self.session.post(url, data=form_data, headers=headers)
        print(f"--- API 回應狀態碼: {response.status_code} ---")
        response.raise_for_status()

        response_content = response.text
        print(f"--- API 原始回應內容 ---\n{response_content}\n--------------------")

        response_signature = response.headers.get('X-iCP-Signature')

        self.rsa_helper.import_pem_public_key(verification_key)
        is_valid = self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature)
        if not is_valid:
            raise Exception("API 回應簽章驗證失敗。")
        print("--- API 回應簽章驗證成功 ---")

        response_json = json.loads(response_content)
        if response_json['RtnCode'] != 1:
            raise Exception(
                f"API 返回錯誤 (RtnCode: {response_json['RtnCode']}): {response_json.get('RtnMsg', '未知錯誤')}")

        if 'EncData' in response_json and response_json['EncData']:
            if is_cert_api:
                decrypted_content = self.rsa_helper.decrypt(response_json['EncData'])
            else:
                decrypted_content = aes_helper.decrypt(response_json['EncData'])
            print(f"--- API 回應 (已解密) ---\n{decrypted_content}\n--------------------")
            return json.loads(decrypted_content)
        return None

    def initialize_connection(self):
        """
        執行與伺服器的初始金鑰交換。
        """
        # 1. Get Default Public Cert
        url = f"{self.base_url}api/member/Certificate/GetDefaultPucCert"
        response = self.session.post(url)
        response.raise_for_status()
        data = response.json()
        if data['RtnCode'] != 1: raise Exception(data['RtnMsg'])
        default_cert_id, default_public_key = data['DefaultPubCertID'], data['DefaultPubCert']
        print("--- 取得預設公鑰成功 ---")

        # 2. Exchange Public Cert
        client_key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_key_pair['private_key']
        self._client_public_key = client_key_pair['public_key']

        self._server_public_key = default_public_key

        payload = {
            'ClientPubCert': "".join(self._client_public_key.splitlines()[1:-1]),
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }
        exchange_result = self._call_api(
            "api/member/Certificate/ExchangePucCert", payload,
            is_cert_api=True, cert_header_name="X-iCP-DefaultPubCertID", cert_id=default_cert_id,
            verification_key=default_public_key
        )

        self._server_public_key = exchange_result['ServerPubCert']
        server_pub_cert_id = exchange_result['ServerPubCertID']
        print("--- 交換公鑰成功，並更新伺服器公鑰 ---")

        # 3. Generate AES
        payload = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        aes_result = self._call_api(
            "api/member/Certificate/GenerateAES", payload,
            is_cert_api=True, cert_header_name="X-iCP-ServerPubCertID", cert_id=server_pub_cert_id
        )
        self._aes_client_cert_id = aes_result['EncKeyID']
        self._aes_key = aes_result['AES_Key']
        self._aes_iv = aes_result['AES_IV']
        print(f"--- AES 金鑰已建立。KeyID: {self._aes_client_cert_id} ---")

    def step1_set_register_info(self):
        """第一步：註冊新用戶並取得 LoginTokenID。"""
        print("\n==================== 步驟 1: 註冊新用戶 ====================")
        self.dynamic_user_code = f"i{int(time.time())}"
        self.dynamic_cellphone = f"0{random.randint(950000000, 959999999)}"

        payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': self.dynamic_cellphone,
            'UserCode': self.dynamic_user_code,
            'UserPwd': 'Aa123456'
        }
        result = self._call_api("app/MemberInfo/SetRegisterInfo2022", payload)
        self.login_token_id = result.get("LoginTokenID")
        if not self.login_token_id:
            raise Exception("未能從步驟 1 的回應中取得 LoginTokenID")
        print(f"--- 狀態更新：取得 LoginTokenID -> {self.login_token_id} ---")

    def step2_send_auth_sms(self):
        """第二步：發送驗證簡訊。"""
        print("\n==================== 步驟 2: 發送驗證簡訊 ====================")
        payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': self.dynamic_cellphone,
            'LoginTokenID': self.login_token_id,
            'SMSAuthType': '1',
            'UserCode': ''
        }
        result = self._call_api("app/MemberInfo/SendAuthSMS", payload)
        self.auth_code = result.get("AuthCode")
        if not self.auth_code:
            raise Exception("未能從步驟 2 的回應中取得 AuthCode")
        print(f"--- 狀態更新：取得 AuthCode -> {self.auth_code} ---")

    def step3_check_register_auth_sms(self):
        """第三步：驗證簡訊碼。"""
        print("\n==================== 步驟 3: 驗證簡訊碼 ====================")
        payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': self.dynamic_cellphone,
            'LoginTokenID': self.login_token_id,
            'AuthCode': self.auth_code
        }
        self._call_api("app/MemberInfo/CheckRegisterAuthSMS", payload)
        print("--- 狀態更新：簡訊驗證成功 ---")

    def step4_auth_idno(self):
        """第四步：驗證身分證資料。"""
        print("\n==================== 步驟 4: 驗證身分資料 ====================")
        self.dynamic_idno = generate_taiwan_id()
        print(f"--- 使用動態產生的身分證: {self.dynamic_idno} ---")

        payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'LoginTokenID': self.login_token_id,
            "Address": "123",
            "AreaID": "1001",
            "BirthDay": "2000-01-01",
            "CName": "測試一",
            "Email": "",
            "Idno": self.dynamic_idno,
            "IssueDate": "2025-05-21",
            "IssueLoc": "64000",
            "IssueType": "3",
            "NationalityID": "1206",
            "fileCols": "img1,img2"
        }
        self._call_api("app/MemberInfo/AuthIDNO", payload)
        print("--- 狀態更新：身分驗證成功 ---")

    def run_full_flow(self):
        """完整執行所有註冊步驟。"""
        try:
            self.initialize_connection()
            self.step1_set_register_info()
            self.step2_send_auth_sms()
            self.step3_check_register_auth_sms()
            self.step4_auth_idno()
            print("\n========================================================")
            print("      🎉🎉🎉 所有註冊流程已成功執行完畢！ 🎉🎉🎉")
            print("========================================================")
        except Exception as e:
            print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print(f"      執行流程時發生錯誤: {e}")
            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")


if __name__ == '__main__':
    flow = FullRegistrationFlow()
    flow.run_full_flow()
