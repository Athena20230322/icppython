import requests
import json
import base64
import os
from datetime import datetime, timedelta

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


class RsaCryptoHelper:
    """
    用於 RSA 加密、解密、簽章和驗證的輔助類別。
    此類別模擬 C# RsaCryptoHelper 的功能。
    """

    def __init__(self):
        self._key = None

    def generate_pem_key(self):
        """
        產生一個新的 2048 位元 RSA 金鑰對。
        私鑰使用 PKCS#8 格式，公鑰使用 SubjectPublicKeyInfo 格式，以提高相容性。
        """
        key = RSA.generate(2048)
        # 匯出為 PKCS#8 格式，這是較現代且廣泛支援的格式
        private_key_pem = key.export_key(format='PEM', pkcs=8).decode('utf-8')
        public_key_pem = key.publickey().export_key(format='PEM').decode('utf-8')
        return {'private_key': private_key_pem, 'public_key': public_key_pem}

    def import_pem_public_key(self, pem_key):
        """
        從 PEM 格式匯入 RSA 公鑰。
        如果金鑰缺少 PEM 頁首/頁尾，會自動添加。
        """
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key):
        """從 PEM 格式匯入 RSA 私鑰。"""
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        """
        使用 RSA 公鑰加密資料，支援長訊息（分塊加密）。
        """
        key_size_bytes = self._key.size_in_bytes()
        max_chunk_size = key_size_bytes - 11  # PKCS#1 v1.5 padding overhead

        data_bytes = data.encode('utf-8')
        encrypted_chunks = []

        for i in range(0, len(data_bytes), max_chunk_size):
            chunk = data_bytes[i:i + max_chunk_size]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            encrypted_chunks.append(cipher_rsa.encrypt(chunk))

        return base64.b64encode(b''.join(encrypted_chunks)).decode('utf-8')

    def decrypt(self, enc_data):
        """
        使用 RSA 私鑰解密資料，支援長訊息（分塊解密）。
        這是為了與 C# 的行為對稱。
        """
        try:
            encrypted_bytes = base64.b64decode(enc_data)
            key_size_bytes = self._key.size_in_bytes()

            decrypted_chunks = []

            for i in range(0, len(encrypted_bytes), key_size_bytes):
                chunk = encrypted_bytes[i:i + key_size_bytes]
                cipher_rsa = PKCS1_v1_5.new(self._key)
                # 使用哨兵物件來偵測解密錯誤
                decrypted_chunks.append(cipher_rsa.decrypt(chunk, 'error_sentinel'))

            if b'error_sentinel' in decrypted_chunks:
                raise ValueError("解密過程中至少有一個區塊失敗。")

            return b''.join(decrypted_chunks).decode('utf-8')
        except Exception:
            raise ValueError("解密失敗，請確認 RSA 金鑰或資料是否正確。")

    def sign_data_with_sha256(self, data):
        """使用 SHA256 和 RSA 簽署資料。"""
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._key).sign(h)
        return base64.b64encode(signature).decode('utf-8')

    def verify_sign_data_with_sha256(self, data, signature):
        """驗證 RSA SHA256 簽章。"""
        h = SHA256.new(data.encode('utf-8'))
        signature_bytes = base64.b64decode(signature)
        try:
            pkcs1_15.new(self._key).verify(h, signature_bytes)
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
    """
    用於 AES 加密和解密 (CBC 模式) 的輔助類別。
    此類別模擬 C# AesCryptoHelper 的功能。
    """

    def __init__(self, key=None, iv=None):
        self.key = key.encode('utf-8') if key else None
        self.iv = iv.encode('utf-8') if iv else None

    def encrypt(self, data):
        """使用 AES CBC 和 PKCS7 填充來加密資料。"""
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        padded_data = pad(data.encode('utf-8'), AES.block_size, style='pkcs7')
        encrypted_bytes = cipher.encrypt(padded_data)
        return base64.b64encode(encrypted_bytes).decode('utf-8')

    def decrypt(self, enc_data):
        """使用 AES CBC 和 PKCS7 填充來解密資料。"""
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        unpadded_bytes = unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7')
        return unpadded_bytes.decode('utf-8')


class CertificateApiClient:
    """
    一個用於與 ICP 憑證 API 互動的客戶端。
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

    def _check_timestamp(self, timestamp_str):
        """驗證時間戳是否在 300 秒的容許範圍內。"""
        try:
            dt = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
            diff = datetime.now() - dt
            if abs(diff.total_seconds()) > 300:  # 增加容錯以應對潛在的時鐘偏差
                print(f"警告：時間戳差異過大：{diff.total_seconds()} 秒，時間戳為 {timestamp_str}")
        except ValueError:
            print(f"無法解析時間戳：{timestamp_str}")

    def get_default_puc_cert(self):
        """從伺服器獲取預設公鑰憑證。"""
        url = f"{self.base_url}api/member/Certificate/GetDefaultPucCert"
        response = self.session.post(url)
        response.raise_for_status()
        data = response.json()
        print(f"回傳：{json.dumps(data, ensure_ascii=False)}")
        if data['RtnCode'] != 1:
            raise Exception(data['RtnMsg'])
        return data['DefaultPubCertID'], data['DefaultPubCert']

    def _call_certificate_api(self, action, cert_id, server_public_key, client_private_key, payload, cert_header_name):
        """對受 RSA 保護的憑證 API 端點進行原始呼叫。"""
        json_payload = json.dumps(payload, ensure_ascii=False)

        self.rsa_helper.import_pem_public_key(server_public_key)
        enc_data = self.rsa_helper.encrypt(json_payload)

        self.rsa_helper.import_pem_private_key(client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        form_data = {'EncData': enc_data}
        headers = {
            cert_header_name: str(cert_id),
            'X-iCP-Signature': signature
        }

        url = f"{self.base_url}{action}"
        response = self.session.post(url, data=form_data, headers=headers)
        response.raise_for_status()

        response_signature = response.headers.get('X-iCP-Signature')
        return response.text, response_signature

    def exchange_puc_cert(self):
        """與伺服器交換公鑰。"""
        default_cert_id, default_public_key = self.get_default_puc_cert()

        client_key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_key_pair['private_key']
        self._client_public_key = client_key_pair['public_key']

        # 移除 ClientPubCert 中的換行符，因為它將在 JSON 中傳遞
        client_pub_cert_oneline = "".join(self._client_public_key.splitlines()[1:-1])

        request_payload = {
            'ClientPubCert': client_pub_cert_oneline,
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }

        content, signature = self._call_certificate_api(
            action="api/member/Certificate/ExchangePucCert",
            cert_id=default_cert_id,
            server_public_key=default_public_key,
            client_private_key=self._client_private_key,
            payload=request_payload,
            cert_header_name="X-iCP-DefaultPubCertID"
        )

        api_result = json.loads(content)
        if api_result['RtnCode'] != 1:
            raise Exception(api_result['RtnMsg'])

        self.rsa_helper.import_pem_private_key(self._client_private_key)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])
        exchange_result = json.loads(decrypted_json)

        self._server_public_key = exchange_result['ServerPubCert']
        self.rsa_helper.import_pem_public_key(self._server_public_key)

        is_valid = self.rsa_helper.verify_sign_data_with_sha256(content, signature)
        if not is_valid:
            raise Exception("金鑰交換期間簽章驗證失敗。")

        self._check_timestamp(exchange_result['Timestamp'])

        print(self._client_private_key)
        print("1234567890")

        return exchange_result

    def generate_aes(self):
        """從伺服器產生並擷取 AES 金鑰。"""
        exchange_result = self.exchange_puc_cert()

        request_payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }

        content, signature = self._call_certificate_api(
            action="api/member/Certificate/GenerateAES",
            cert_id=exchange_result['ServerPubCertID'],
            server_public_key=self._server_public_key,
            client_private_key=self._client_private_key,
            payload=request_payload,
            cert_header_name="X-iCP-ServerPubCertID"
        )

        api_result = json.loads(content)
        if api_result['RtnCode'] != 1:
            raise Exception(api_result['RtnMsg'])

        self.rsa_helper.import_pem_private_key(self._client_private_key)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])

        print("168168168")
        print(decrypted_json)

        generate_aes_result = json.loads(decrypted_json)

        self.rsa_helper.import_pem_public_key(self._server_public_key)
        is_valid = self.rsa_helper.verify_sign_data_with_sha256(content, signature)
        if not is_valid:
            raise Exception("AES 產生期間簽章驗證失敗。")

        self._check_timestamp(generate_aes_result['Timestamp'])

        self._aes_client_cert_id = generate_aes_result['EncKeyID']
        self._aes_key = generate_aes_result['AES_Key']
        self._aes_iv = generate_aes_result['AES_IV']

        print("167167167")
        print(self._aes_client_cert_id)

    def _call_normal_api(self, action, payload):
        """對一個常規的、受 AES 加密的 API 端點進行呼叫。"""
        json_payload = json.dumps(payload)

        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        enc_data = aes_helper.encrypt(json_payload)

        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        print("123123455")
        print(signature)
        print("123123456")

        form_data = {'EncData': enc_data}
        headers = {
            'X-iCP-EncKeyID': str(self._aes_client_cert_id),
            'X-iCP-Signature': signature
        }

        url = f"{self.base_url}{action}"
        response = self.session.post(url, data=form_data, headers=headers)
        response.raise_for_status()

        response_signature = response.headers.get('X-iCP-Signature')
        response_content = response.text

        self.rsa_helper.import_pem_public_key(self._server_public_key)
        is_valid = self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature)
        if not is_valid:
            raise Exception("一般 API 呼叫的簽章驗證失敗。")

        response_json = json.loads(response_content)
        if response_json['RtnCode'] != 1:
            raise Exception(response_json['RtnMsg'])

        decrypted_content = aes_helper.decrypt(response_json['EncData'])
        print("LoginTokenID")
        print(decrypted_content)

        try:
            decrypted_data_json = json.loads(decrypted_content)
            login_token_id = decrypted_data_json.get("LoginTokenID", "").split(',')[0]
            print(login_token_id)

            # --- FIX: Write file to the script's directory ---
            # 取得程式碼所在的資料夾路徑
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # 組合出完整的輸出檔案路徑
            output_file_path = os.path.join(script_dir, "logintokenid.txt")

            # 將 Token 寫入到指定的路徑
            with open(output_file_path, "w") as f:
                f.write(login_token_id)
            print(f"LoginTokenID 已成功儲存至：{output_file_path}")
            # --- END FIX ---

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"無法提取 LoginTokenID: {e}")

        self._check_timestamp(json.loads(decrypted_content)['Timestamp'])
        return response_content

    def refresh_login_token(self):
        """執行完整序列以獲取更新的登入權杖。"""
        self.generate_aes()

        url = "app/MemberInfo/RefreshLoginToken"
        request_payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': '0976100006'
        }

        response = self._call_normal_api(url, request_payload)

        print("LoginTokenID")
        print(response)


if __name__ == '__main__':
    client = CertificateApiClient()
    try:
        client.refresh_login_token()
    except Exception as e:
        print(f"發生錯誤：{e}")
