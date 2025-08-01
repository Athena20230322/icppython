import requests
import json
import base64
import os
import random
import string
from datetime import datetime

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, AES
from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15
from Crypto.Util.Padding import pad, unpad

# ==============================================================================
# === 請在此處設定您的測試帳號資訊 ===
# 將下面的值替換為您在 Postman 中測試成功的帳號、密碼和手機號碼
# ==============================================================================
TEST_ACCOUNT_CONFIG = {
    "CELLPHONE": "0935123456",  # 請替換為您的測試手機
    "USER_CODE": "hncb202301",  # 請替換為您的測試帳號
    "PASSWORD": "Aa123456"      # 請替換為您的測試密碼
}
# ==============================================================================


# --- 加密輔助類別 ---
class RsaCryptoHelper:
    def __init__(self): self._key = None
    def generate_pem_key(self):
        key = RSA.generate(2048)
        private_key_pem = key.export_key(format='PEM', pkcs=8).decode('utf-8')
        public_key_pem = key.publickey().export_key(format='PEM').decode('utf-8')
        return {'private_key': private_key_pem, 'public_key': public_key_pem}
    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith('-----BEGIN'):
            pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)
    def import_pem_private_key(self, pem_key): self._key = RSA.import_key(pem_key)
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
            if b'error_sentinel' in decrypted_chunks: raise ValueError("解密過程中至少有一個區塊失敗。")
            return b''.join(decrypted_chunks).decode('utf-8')
        except Exception: raise ValueError("解密失敗，請確認 RSA 金鑰或資料是否正確。")
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
        except (ValueError, TypeError): return False

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
        if not enc_data: return ""
        encrypted_bytes = base64.b64decode(enc_data)
        cipher = AES.new(self.key, AES.MODE_CBC, self.iv)
        decrypted_padded_bytes = cipher.decrypt(encrypted_bytes)
        unpadded_bytes = unpad(decrypted_padded_bytes, AES.block_size, style='pkcs7')
        return unpadded_bytes.decode('utf-8')


# --- API 客戶端主類別 ---
class CertificateApiClient:
    def __init__(self,
                 member_base_url="https://icp-member-stage.icashpay.com.tw/",
                 payment_base_url="https://icp-payment-stage.icashpay.com.tw/",
                 pluspayment_base_url="https://icp-plus-stage.icashpay.com.tw",
                 data_dir="C:\\icppython"):
        self.member_base_url = member_base_url
        self.payment_base_url = payment_base_url
        self.pluspayment_base_url = pluspayment_base_url
        self.data_dir = data_dir
        self.rsa_helper = RsaCryptoHelper()
        self.session = requests.Session()
        self._server_public_key = None
        self._client_private_key = None
        self._aes_client_cert_id = -1
        self._aes_key = None
        self._aes_iv = None
        os.makedirs(self.data_dir, exist_ok=True)

    def _check_timestamp(self, timestamp_str):
        if not timestamp_str: return
        try:
            dt = datetime.strptime(timestamp_str, "%Y/%m/%d %H:%M:%S")
            diff = datetime.now() - dt
            if abs(diff.total_seconds()) > 300:
                print(f"警告：時間戳差異過大：{diff.total_seconds():.2f} 秒，時間戳為 {timestamp_str}")
        except ValueError:
            print(f"無法解析時間戳：{timestamp_str}")

    def _call_normal_api(self, base_url, action, payload):
        json_payload = json.dumps(payload, ensure_ascii=False)
        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        enc_data = aes_helper.encrypt(json_payload)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        form_data = {'EncData': enc_data}
        headers = {
            'X-iCP-EncKeyID': str(self._aes_client_cert_id),
            'X-iCP-Signature': signature
        }
        full_url = f"{base_url.rstrip('/')}/{action.lstrip('/')}"
        print(f"正在呼叫 API: {full_url}")
        response = self.session.post(full_url, data=form_data, headers=headers)
        response.raise_for_status()
        response_content = response.text

        if action == "app/Payment/ParserQrCode":
            print(f"偵測到特殊 API '{action}'，將嘗試直接解析回應。")
            try:
                response_json = json.loads(response_content)
                if response_json.get('RtnCode') != 1:
                    raise Exception(f"API ({action}) 錯誤: {response_json.get('RtnMsg')} (RtnCode: {response_json.get('RtnCode')})")
                return response_json
            except json.JSONDecodeError:
                raise Exception(f"API ({action}) 回應了非 JSON 的錯誤訊息: '{response_content}'")
        else:
            response_signature = response.headers.get('X-iCP-Signature')
            if response_signature:
                self.rsa_helper.import_pem_public_key(self._server_public_key)
                if not self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature):
                    raise Exception(f"API ({action}) 回應的簽章驗證失敗。")
                else:
                    print(f"API ({action}) 回應的簽章驗證成功。")
            else:
                print(f"警告：API ({action}) 的回應中未包含 'X-iCP-Signature' 標頭，跳過簽章驗證。")
            
            response_json = json.loads(response_content)
            if response_json['RtnCode'] != 1:
                raise Exception(f"API ({action}) 錯誤: {response_json['RtnMsg']} (RtnCode: {response_json['RtnCode']})")

            decrypted_content_str = aes_helper.decrypt(response_json['EncData'])
            if not decrypted_content_str:
                return {}
            decrypted_data = json.loads(decrypted_content_str)
            self._check_timestamp(decrypted_data.get('Timestamp'))
            return decrypted_data

    def _ensure_aes_session(self):
        if self._aes_key and self._aes_iv: return
        print("AES Session 未建立，開始建立流程...")
        default_cert_id, default_public_key = self.get_default_puc_cert()
        client_key_pair = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_key_pair['private_key']
        self._client_public_key = client_key_pair['public_key']
        client_pub_cert_oneline = "".join(self._client_public_key.splitlines()[1:-1])
        exchange_payload = {'ClientPubCert': client_pub_cert_oneline,'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        print("正在交換公鑰...")
        content, signature = self._call_certificate_api("api/member/Certificate/ExchangePucCert",default_cert_id,default_public_key,self._client_private_key,exchange_payload,"X-iCP-DefaultPubCertID")
        api_result = json.loads(content)
        if api_result['RtnCode'] != 1: raise Exception(f"ExchangePucCert 失敗: {api_result['RtnMsg']}")
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])
        exchange_result = json.loads(decrypted_json)
        self._server_public_key = exchange_result['ServerPubCert']
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(content, signature): raise Exception("金鑰交換期間簽章驗證失敗。")
        self._check_timestamp(exchange_result['Timestamp'])
        print("公鑰交換成功。")
        generate_aes_payload = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        print("正在請求 AES 金鑰...")
        content, signature = self._call_certificate_api("api/member/Certificate/GenerateAES",exchange_result['ServerPubCertID'],self._server_public_key,self._client_private_key,generate_aes_payload,"X-iCP-ServerPubCertID")
        api_result = json.loads(content)
        if api_result['RtnCode'] != 1: raise Exception(f"GenerateAES 失敗: {api_result['RtnMsg']}")
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        decrypted_json = self.rsa_helper.decrypt(api_result['EncData'])
        generate_aes_result = json.loads(decrypted_json)
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(content, signature): raise Exception("AES 產生期間簽章驗證失敗。")
        self._check_timestamp(generate_aes_result['Timestamp'])
        self._aes_client_cert_id = generate_aes_result['EncKeyID']
        self._aes_key = generate_aes_result['AES_Key']
        self._aes_iv = generate_aes_result['AES_IV']
        print(f"AES 金鑰已成功建立。KeyID: {self._aes_client_cert_id}")
        print("\n" + "*"*15 + " AES 金鑰資訊 " + "*"*15)
        print(f"AES Key: {self._aes_key}")
        print(f"AES IV : {self._aes_iv}")
        print("*"*47 + "\n")


    def get_default_puc_cert(self):
        print("正在取得伺服器預設公鑰...")
        url = f"{self.member_base_url}api/member/Certificate/GetDefaultPucCert"
        response = self.session.post(url)
        response.raise_for_status()
        data = response.json()
        if data['RtnCode'] != 1: raise Exception(f"GetDefaultPucCert 失敗: {data['RtnMsg']}")
        print("成功取得伺服器預設公鑰。")
        return data['DefaultPubCertID'], data['DefaultPubCert']
        
    def _call_certificate_api(self, action, cert_id, server_public_key, client_private_key, payload, cert_header_name):
        json_payload = json.dumps(payload, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(server_public_key)
        enc_data = self.rsa_helper.encrypt(json_payload)
        self.rsa_helper.import_pem_private_key(client_private_key)
        signature = self.rsa_helper.sign_data_with_sha256(enc_data)
        form_data = {'EncData': enc_data}
        headers = {cert_header_name: str(cert_id),'X-iCP-Signature': signature}
        url = f"{self.member_base_url}{action}"
        response = self.session.post(url, data=form_data, headers=headers)
        response.raise_for_status()
        response_signature = response.headers.get('X-iCP-Signature')
        return response.text, response_signature
        
    def step1_refresh_login_token(self):
        self._ensure_aes_session()
        request_payload = {
            'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            'CellPhone': TEST_ACCOUNT_CONFIG["CELLPHONE"]
        }
        decrypted_data = self._call_normal_api(self.member_base_url, "app/MemberInfo/RefreshLoginToken", request_payload)
        try:
            login_token_id = decrypted_data.get("LoginTokenID", "").split(',')[0]
            output_file_path = os.path.join(self.data_dir, "logintokenid.txt")
            with open(output_file_path, "w") as f: f.write(login_token_id)
            print(f"成功取得 LoginTokenID: {login_token_id}")
            print(f"已儲存至: {output_file_path}")
        except (KeyError, IndexError) as e: raise Exception(f"無法從回應中提取 LoginTokenID: {e}")

    def step2_send_auth_sms(self):
        self._ensure_aes_session()
        login_token_file = os.path.join(self.data_dir, "logintokenid.txt")
        try:
            with open(login_token_file, 'r') as f: login_token_id = f.read().strip()
            if not login_token_id: raise ValueError("logintokenid.txt 是空的。")
        except FileNotFoundError: raise FileNotFoundError(f"找不到 Token 檔案: {login_token_file}，請先執行 step1。")
        request_payload = {
            "Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "CellPhone": TEST_ACCOUNT_CONFIG["CELLPHONE"],
            "SMSAuthType": 5,
            "UserCode": "",
            "LoginTokenID": login_token_id
        }
        decrypted_data = self._call_normal_api(self.member_base_url, "app/MemberInfo/SendAuthSMS", request_payload)
        try:
            auth_code = decrypted_data.get("AuthCode")
            if auth_code is None: raise KeyError("回應中未找到 'AuthCode'。")
            output_file_path = os.path.join(self.data_dir, "authcode.txt")
            with open(output_file_path, "w") as f: f.write(auth_code)
            print(f"成功取得 AuthCode: {auth_code}")
            print(f"已儲存至: {output_file_path}")
        except KeyError as e: raise Exception(f"無法從回應中提取 AuthCode: {e}")

    def step3_login(self):
        self._ensure_aes_session()
        auth_code_file = os.path.join(self.data_dir, "authcode.txt")
        try:
            with open(auth_code_file, 'r') as f: auth_code = f.read().strip()
            if not auth_code: raise ValueError("authcode.txt 是空的。")
        except FileNotFoundError: raise FileNotFoundError(f"找不到驗證碼檔案: {auth_code_file}，請先執行 step2。")
        login_payload = {
            "Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
            "LoginType": "1",
            "UserCode": TEST_ACCOUNT_CONFIG["USER_CODE"],
            "UserPwd": TEST_ACCOUNT_CONFIG["PASSWORD"],
            "SMSAuthCode": auth_code
        }
        self._call_normal_api(self.member_base_url, "app/MemberInfo/UserCodeLogin2022", login_payload)
        print("使用者登入成功！")

    def step4_parse_qr_code(self, qr_code_data):
        self._ensure_aes_session()
        payload = {"Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"), "MerchantQRcode": qr_code_data}
        return self._call_normal_api(self.pluspayment_base_url, "app/Payment/ParserQrCode", payload)

    def decrypt_aes_data(self, encrypted_data_str):
        """一個公開的方法，使用當前 session 的 AES 金鑰來解密字串。"""
        if not self._aes_key or not self._aes_iv:
            raise Exception("AES session 未建立，無法解密。")
        aes_helper = AesCryptoHelper(self._aes_key, self._aes_iv)
        return aes_helper.decrypt(encrypted_data_str)


def run_interactive_mode(client):
    """執行互動模式，讓使用者可以重複輸入 QR Code 進行解析。"""
    print("\n" + "=" * 40)
    print("=== 互動模式已啟動 ===")
    print("您已成功登入，現在可以重複解析 QR Code。")
    print("請直接貼上 MerchantQRcode 字串並按下 Enter。")
    print("若要離開程式，請直接輸入 'exit' 或 'quit'。")
    print("=" * 40)
    while True:
        qr_code_input = input("\n請輸入 MerchantQRcode > ").strip()
        if qr_code_input.lower() in ['exit', 'quit']:
            print("正在離開程式...")
            break
        if not qr_code_input: continue
        try:
            print(f"----- [正在解析] -----")
            # 步驟一：呼叫API並取得原始回應
            response = client.step4_parse_qr_code(qr_code_input)
            
            # 步驟二：檢查並解密EncData
            enc_data_to_decrypt = response.get("EncData")
            if enc_data_to_decrypt:
                decrypted_payload = client.decrypt_aes_data(enc_data_to_decrypt)
                
                # 步驟三：進行兩層解析並提取所需的值
                print("\n--- [解析結果] ---")
                try:
                    # 解析第一層
                    outer_json = json.loads(decrypted_payload)
                    # 準備一個字典來存放最終結果
                    filtered_result = {}
                    
                    # 從第一層提取 'CodeType'
                    filtered_result['CodeType'] = outer_json.get('CodeType', 'N/A')

                    # 提取並解析第二層 ('RtnValue')
                    rtn_value_str = outer_json.get('RtnValue')
                    if rtn_value_str and isinstance(rtn_value_str, str):
                        try:
                            inner_json = json.loads(rtn_value_str)
                            # 從第二層提取 'QRCodeType' 和 'UsePointType'
                            filtered_result['QRCodeType'] = inner_json.get('QRCodeType', 'N/A')
                            filtered_result['UsePointType'] = inner_json.get('UsePointType', 'N/A')
                        except json.JSONDecodeError:
                             print("警告: 'RtnValue' 欄位的內容不是有效的 JSON 格式。")
                             filtered_result['QRCodeType'] = '解析錯誤'
                             filtered_result['UsePointType'] = '解析錯誤'
                    else:
                        filtered_result['QRCodeType'] = 'N/A'
                        filtered_result['UsePointType'] = 'N/A'
                    
                    # 步驟四：印出篩選後的結果
                    print(json.dumps(filtered_result, indent=4, ensure_ascii=False))

                except json.JSONDecodeError:
                    print("錯誤: 解密後的 EncData 不是有效的 JSON 格式。")
                    print(f"原始解密內容: {decrypted_payload}")
            else:
                 print("\n--- [回應中無 EncData 或為空] ---")
            
            print("-" * 20)

        except Exception as e:
            print(f"\n*** [解析錯誤] ***")
            print(f"錯誤訊息: {e}")
            print("-" * 20)

if __name__ == '__main__':
    api_client = CertificateApiClient()
    try:
        print(">>> 使用設定檔中的帳號資訊進行登入流程 <<<")
        print(f'手機: {TEST_ACCOUNT_CONFIG["CELLPHONE"]}, 帳號: {TEST_ACCOUNT_CONFIG["USER_CODE"]}')
        print("-" * 30 + "\n")
        
        # --- 一次性登入流程 ---
        print("--- 步驟 1: 刷新 Login Token ---")
        api_client.step1_refresh_login_token()
        print("-" * 30 + "\n")
        print("--- 步驟 2: 發送 SMS 驗證碼 ---")
        api_client.step2_send_auth_sms()
        print("-" * 30 + "\n")
        print("--- 步驟 3: 使用者登入 ---")
        api_client.step3_login()
        print("-" * 30 + "\n")
        # --- 進入互動模式 ---
        run_interactive_mode(api_client)
    except Exception as e:
        print(f"\n程式在初始化或登入時發生嚴重錯誤: {e}")