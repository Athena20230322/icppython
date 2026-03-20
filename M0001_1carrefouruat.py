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
                raise ValueError("解密失敗。")
            return b''.join(decrypted_chunks).decode('utf-8')
        except Exception:
            raise ValueError("解密失敗，請確認 RSA 金鑰或資料是否正確。")

    def sign_data_with_sha256(self, data):
        h = SHA256.new(data.encode('utf-8'))
        signature = pkcs1_15.new(self._key).sign(h)
        return base64.b64encode(signature).decode('utf-8')

    def verify_sign_data_with_sha256(self, data, signature):
        h = SHA256.new(data.encode('utf-8'))
        signature_bytes = base64.b64decode(signature)
        try:
            pkcs1_15.new(self._key).verify(h, signature_bytes)
            return True
        except (ValueError, TypeError):
            return False


class AesCryptoHelper:
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


class CertificateApiClient:
    def __init__(self, base_url="https://icp-member-preprod.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key = None
        self._client_private_key = None
        self._aes_client_cert_id = -1
        self._aes_key = None
        self._aes_iv = None

    def _read_config(self, filename, default_val):
        """讀取 C:\icppython 中的設定檔"""
        path = os.path.join(r"C:\icppython", filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content: return content
            except Exception as e:
                print(f"讀取 {filename} 失敗: {e}")
        return default_val

    def get_default_puc_cert(self):
        url = f"{self.base_url}api/member/Certificate/GetDefaultPucCert"
        response = self.session.post(url)
        data = response.json()
        if data['RtnCode'] != 1: raise Exception(data['RtnMsg'])
        return data['DefaultPubCertID'], data['DefaultPubCert']

    def _call_certificate_api(self, action, cert_id, server_public_key, client_private_key, payload, cert_header_name):
        json_payload = json.dumps(payload, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(server_public_key)
        enc_data = self.rsa_helper.encrypt(json_payload)
        self.rsa_helper.import_pem_private_key(client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        headers = {cert_header_name: str(cert_id), 'X-iCP-Signature': signature}
        url = f"{self.base_url}{action}"
        response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        return response.text, response.headers.get('X-iCP-Signature')

    def exchange_puc_cert(self):
        default_cert_id, default_public_key = self.get_default_puc_cert()
        client_key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_key_pair['private_key']
        client_pub_oneline = "".join(client_key_pair['public_key'].splitlines()[1:-1])

        request_payload = {
            'ClientPubCert': client_pub_oneline,
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        }

        content, signature = self._call_certificate_api(
            "api/member/Certificate/ExchangePucCert", default_cert_id, default_public_key,
            self._client_private_key, request_payload, "X-iCP-DefaultPubCertID"
        )
        api_result = json.loads(content)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])
        exchange_result = json.loads(decrypted_json)
        self._server_public_key = exchange_result['ServerPubCert']
        return exchange_result

    def generate_aes(self):
        exchange_result = self.exchange_puc_cert()
        request_payload = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        content, _ = self._call_certificate_api(
            "api/member/Certificate/GenerateAES", exchange_result['ServerPubCertID'],
            self._server_public_key, self._client_private_key, request_payload, "X-iCP-ServerPubCertID"
        )
        api_result = json.loads(content)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])
        gen_aes_res = json.loads(decrypted_json)
        self._aes_client_cert_id = gen_aes_res['EncKeyID']
        self._aes_key = gen_aes_res['AES_Key']
        self._aes_iv = gen_aes_res['AES_IV']

    def _call_normal_api(self, action, payload):
        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        enc_data = aes_helper.encrypt(json.dumps(payload))
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        headers = {'X-iCP-EncKeyID': str(self._aes_client_cert_id), 'X-iCP-Signature': signature}
        response = self.session.post(f"{self.base_url}{action}", data={'EncData': enc_data}, headers=headers)
        res_json = response.json()
        decrypted_content = aes_helper.decrypt(res_json['EncData'])

        # 儲存 Token
        token_id = json.loads(decrypted_content).get("LoginTokenID", "").split(',')[0]
        output_path = r"C:\icppython\logintokenid.txt"
        with open(output_path, "w") as f: f.write(token_id)
        print(f"Token 已儲存至: {output_path}")
        return decrypted_content

    def refresh_login_token(self):
        self.generate_aes()
        # --- 讀取外部手機號碼 ---
        cellphone = self._read_config("cellphone.txt", "0976109035")

        url = "app/MemberInfo/RefreshLoginToken"
        payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': cellphone
        }
        print(f"正在執行 RefreshLoginToken，手機號碼: {cellphone}")
        self._call_normal_api(url, payload)


if __name__ == '__main__':
    client = CertificateApiClient()
    try:
        client.refresh_login_token()
    except Exception as e:
        print(f"發生錯誤：{e}")