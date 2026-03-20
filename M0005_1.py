import requests
import json
import base64
from datetime import datetime
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad


# --- RSA & AES 輔助類別 (保持與先前一致，確保 PEM 格式正確) ---
class RsaCryptoHelper:
    def __init__(self): self._key = None

    def generate_pem_key(self):
        key = RSA.generate(2048)
        return {'private_key': key.export_key().decode('utf-8'),
                'public_key': key.publickey().export_key().decode('utf-8')}

    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key): self._key = RSA.import_key(pem_key.strip())

    def encrypt(self, data):
        key_size = self._key.size_in_bytes()
        max_chunk = key_size - 11
        data_bytes = data.encode('utf-8')
        encrypted = [PKCS1_v1_5.new(self._key).encrypt(data_bytes[i:i + max_chunk]) for i in
                     range(0, len(data_bytes), max_chunk)]
        return base64.b64encode(b''.join(encrypted)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes = base64.b64decode(enc_data)
        key_size = self._key.size_in_bytes()
        decrypted = [PKCS1_v1_5.new(self._key).decrypt(encrypted_bytes[i:i + key_size], b'error') for i in
                     range(0, len(encrypted_bytes), key_size)]
        return b''.join(decrypted).decode('utf-8')

    def sign_data_with_sha256(self, data):
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
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        return unpad(cipher.decrypt(base64.b64decode(enc_data)), 16).decode('utf-8')


class CertificateApiClient:
    def __init__(self, base_url="https://icp-member-stage.icashpay.com.tw/"):
        self.base_url = base_url
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._aes_key = None;
        self._aes_iv = None;
        self._aes_client_cert_id = -1
        self._client_private_key = None;
        self._server_public_key = None

    def exchange_puc_cert(self):
        res_puc = self.session.post(f"{self.base_url}api/member/Certificate/GetDefaultPucCert").json()
        key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = key_pair['private_key']
        client_pub_oneline = "".join(key_pair['public_key'].splitlines()[1:-1])
        payload = {'ClientPubCert': client_pub_oneline, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        self.rsa_helper.import_pem_public_key(res_puc['DefaultPubCert'])
        enc_data = self.rsa_helper.encrypt(json.dumps(payload))
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        res = self.session.post(f"{self.base_url}api/member/Certificate/ExchangePucCert",
                                data={'EncData': enc_data},
                                headers={'X-iCP-DefaultPubCertID': str(res_puc['DefaultPubCertID']),
                                         'X-iCP-Signature': signature}).json()
        self._server_public_key = json.loads(self.rsa_helper.decrypt(res['EncData']))['ServerPubCert']

    def generate_aes(self):
        self.exchange_puc_cert()
        payload = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        enc_data = self.rsa_helper.encrypt(json.dumps(payload))
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        res = self.session.post(f"{self.base_url}api/member/Certificate/GenerateAES",
                                data={'EncData': enc_data},
                                headers={'X-iCP-ServerPubCertID': "1", 'X-iCP-Signature': signature}).json()
        aes_res = json.loads(self.rsa_helper.decrypt(res['EncData']))
        self._aes_key, self._aes_iv, self._aes_client_cert_id = aes_res['AES_Key'], aes_res['AES_IV'], aes_res[
            'EncKeyID']

    def _call_normal_api(self, action, payload):
        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        enc_data = aes_helper.encrypt(json.dumps(payload))
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)

        response = self.session.post(f"{self.base_url}{action}",
                                     data={'EncData': enc_data},
                                     headers={'X-iCP-EncKeyID': str(self._aes_client_cert_id),
                                              'X-iCP-Signature': signature}).json()

        # --- 核心修正：判斷是否有 EncData 欄位 ---
        decrypted_content = {}
        if 'EncData' in response and response['EncData']:
            try:
                decrypted_str = aes_helper.decrypt(response['EncData'])
                decrypted_content = json.loads(decrypted_str)
            except Exception as e:
                print(f"解密失敗: {e}")

        return decrypted_content, response

    def login_attempt(self):
        self.generate_aes()
        login_payload = {"LoginType": 1, "SMSAuthCode": "", "UserCode": "tester230", "UserPwd": "Aa123456"}
        print(f"嘗試登入 (取得 Token)... UserCode: {login_payload['UserCode']}")

        decrypted_res, raw = self._call_normal_api("app/MemberInfo/UserCodeLogin2022", login_payload)

        rtn_code = raw.get('RtnCode')
        print(f"RtnCode: {rtn_code} ({raw.get('RtnMsg')})")

        if rtn_code == 200017:
            # LoginTokenID 可能在解密後的欄位，也可能直接在 raw 裡面 (依據 API 設計)
            token = decrypted_res.get("LoginTokenID") or raw.get("LoginTokenID")
            if token:
                with open("C:\\icppython\\logintokenid.txt", "w") as f:
                    f.write(str(token))
                print(f"成功儲存 LoginTokenID: {token}")
            else:
                print("未找到 LoginTokenID，請檢查 API 回傳結構：", raw)
        else:
            print("未能觸發 200017，回應內容：", raw)


if __name__ == '__main__':
    try:
        CertificateApiClient().login_attempt()
    except Exception as e:
        print(f"執行失敗：{e}")