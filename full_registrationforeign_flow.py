import requests
import json
import base64
import os
import sys
from datetime import datetime
import random
import traceback
import webbrowser

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
LAST_PHONE_FILE = os.path.join(BASE_PATH, "last_phone_foreigner.txt")
LAST_IDNO_FILE = os.path.join(BASE_PATH, "last_idno_foreigner.txt")
TOKEN_FILE = os.path.join(BASE_PATH, "reglogintokenid_foreigner.txt")
AUTH_CODE_FILE = os.path.join(BASE_PATH, "regauthcode_foreigner.txt")
REGISTRATION_LOG_FILE = os.path.join(BASE_PATH, "registration_log_foreigner.txt")


# --- HTML 報告產生類別 ---
class HtmlReporter:
    """產生並儲存一個 HTML 格式的測試報告。"""

    def __init__(self, report_title):
        self.report_title = report_title
        self.steps = []
        self.start_time = datetime.now()
        self.end_time = None
        self.overall_status = "⏳ 執行中"

    def add_step(self, step_name, status, request_payload, decrypted_response=None, error_details=None):
        """新增一個 API 呼叫步驟到報告中。"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        details = {}
        if request_payload:
            payload_to_log = {k: v for k, v in request_payload.items() if not isinstance(v, tuple)}
            details["Request (解密後)"] = json.dumps(payload_to_log, indent=2, ensure_ascii=False)
        if decrypted_response:
            details["Response (解密後)"] = json.dumps(decrypted_response, indent=2, ensure_ascii=False)
        if error_details:
            details["Error Info"] = error_details

        self.steps.append({
            "name": step_name,
            "status": status,
            "timestamp": timestamp,
            "details": details
        })
        if "❌" in status:
            self.overall_status = "❌ 失敗"

    def finalize_report(self):
        """設定報告的最終狀態。"""
        self.end_time = datetime.now()
        if self.overall_status == "⏳ 執行中":
            self.overall_status = "✅ 成功"

    def generate_html(self):
        """產生完整的 HTML 報告內容。"""
        if not self.end_time:
            self.finalize_report()
        duration = self.end_time - self.start_time
        status_color = '#28a745' if '✅' in self.overall_status else '#dc3545'
        html = f"""
        <!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{self.report_title}</title>
        <style>
            body {{ font-family: 'Segoe UI', 'Microsoft JhengHei', '微軟正黑體', sans-serif; margin: 0; padding: 0; background-color: #f4f7f6; color: #333; }}
            .container {{ max-width: 1200px; margin: 20px auto; padding: 20px; background-color: #fff; box-shadow: 0 0 15px rgba(0,0,0,0.1); border-radius: 8px; }}
            h1 {{ color: #2c3e50; text-align: center; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 5px solid {status_color}; }}
            .summary p {{ margin: 5px 0; font-size: 1.1em;}} .summary-status {{ font-size: 1.3em; font-weight: bold; color: {status_color}; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; table-layout: fixed; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; vertical-align: top; word-wrap: break-word; }}
            th {{ background-color: #3498db; color: white; }} tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .status-success {{ color: #28a745; font-weight: bold; }} .status-failure {{ color: #dc3545; font-weight: bold; }}
            details {{ cursor: pointer; margin-top: 10px; }} summary {{ font-weight: bold; list-style-position: inside; }}
            pre {{ background-color: #2d2d2d; color: #f2f2f2; padding: 10px; border-radius: 5px; white-space: pre-wrap; word-wrap: break-word; font-family: 'Courier New', Courier, monospace; font-size: 0.9em; }}
        </style></head><body><div class="container"><h1>{self.report_title}</h1><div class="summary">
        <p><strong>整體狀態:</strong> <span class="summary-status">{self.overall_status}</span></p><p><strong>開始時間:</strong> {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>結束時間:</strong> {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}</p><p><strong>總耗時:</strong> {str(duration).split('.')[0]}</p></div><table>
        <colgroup><col style="width: 5%;"><col style="width: 25%;"><col style="width: 10%;"><col style="width: 15%;"><col style="width: 45%;"></colgroup>
        <thead><tr><th>#</th><th>執行動作</th><th>狀態</th><th>時間戳</th><th>詳細資料</th></tr></thead><tbody>
        """
        for i, step in enumerate(self.steps, 1):
            status_class = "status-success" if "✅" in step['status'] else "status-failure"
            details_html = ""
            for key, value in step['details'].items():
                details_html += f"""<details><summary>{key}</summary><pre><code>{value}</code></pre></details>"""
            html += f"""<tr><td>{i}</td><td>{step['name']}</td><td class="{status_class}">{step['status']}</td><td>{step['timestamp']}</td><td>{details_html}</td></tr>"""
        html += """</tbody></table></div></body></html>"""
        return html

    def save_and_open_report(self, base_path):
        os.makedirs(base_path, exist_ok=True)
        # (***程式碼修改處***) 移除時間格式中的冒號(:)，避免在 Windows 系統產生不合法的檔名
        filename = f"Registration_Report_Foreigner_{self.start_time.strftime('%Y%m%d_%H%M%S')}.html"
        filepath = os.path.join(base_path, filename)
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.generate_html())
            print(f"\n📄 報告已成功生成: {filepath}")
            webbrowser.open(f'file://{os.path.realpath(filepath)}')
        except Exception as e:
            print(f"\n❌ 錯誤: 無法儲存或開啟報告: {e}")


# --- 共用函式 ---
def generate_final_valid_old_arc_id():
    """產生一個隨機且校驗碼有效的「舊式」居留證號，第二碼字母限於 A,B,C,D。"""
    letter_map = {'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15, 'G': 16, 'H': 17, 'I': 34, 'J': 18, 'K': 19,
                  'L': 20, 'M': 21, 'N': 22, 'O': 35, 'P': 23, 'Q': 24, 'R': 25, 'S': 26, 'T': 27, 'U': 28, 'V': 29,
                  'W': 32, 'X': 30, 'Y': 31, 'Z': 33}
    l1_char = random.choice('ABCDEFGHJKLMNPQRSTUVXYWZ')
    l2_char = random.choice('ABCD')
    middle_digits_str = ''.join(random.choices('0123456789', k=7))
    l1_val, l2_val = letter_map[l1_char], letter_map[l2_char]
    d1, d2, d3 = l1_val // 10, l1_val % 10, l2_val % 10
    all_digits = [int(d) for d in middle_digits_str]
    s = (d1 * 1) + (d2 * 9) + (d3 * 8) + (all_digits[0] * 7) + (all_digits[1] * 6) + \
        (all_digits[2] * 5) + (all_digits[3] * 4) + (all_digits[4] * 3) + \
        (all_digits[5] * 2) + (all_digits[6] * 1)
    checksum = (10 - (s % 10)) % 10
    return f"{l1_char}{l2_char}{middle_digits_str}{checksum}"


def get_next_phone_number(start_number=980001817):
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
        private_key_pem, public_key_pem = key.export_key(format='PEM', pkcs=8).decode(
            'utf-8'), key.publickey().export_key(format='PEM').decode('utf-8')
        return {'private_key': private_key_pem, 'public_key': public_key_pem}

    def import_pem_public_key(self, pem_key):
        if not pem_key.strip().startswith(
            '-----BEGIN'): pem_key = f"-----BEGIN PUBLIC KEY-----\n{pem_key}\n-----END PUBLIC KEY-----"
        self._key = RSA.import_key(pem_key)

    def import_pem_private_key(self, pem_key):
        self._key = RSA.import_key(pem_key)

    def encrypt(self, data):
        key_size_bytes, data_bytes, encrypted_chunks = self._key.size_in_bytes(), data.encode('utf-8'), []
        max_chunk_size = key_size_bytes - 11
        for i in range(0, len(data_bytes), max_chunk_size):
            chunk = data_bytes[i:i + max_chunk_size]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            encrypted_chunks.append(cipher_rsa.encrypt(chunk))
        return base64.b64encode(b''.join(encrypted_chunks)).decode('utf-8')

    def decrypt(self, enc_data):
        encrypted_bytes, key_size_bytes, decrypted_chunks = base64.b64decode(enc_data), self._key.size_in_bytes(), []
        for i in range(0, len(encrypted_bytes), key_size_bytes):
            chunk = encrypted_bytes[i:i + key_size_bytes]
            cipher_rsa = PKCS1_v1_5.new(self._key)
            decrypted_chunks.append(cipher_rsa.decrypt(chunk, b'error_sentinel'))
        if b'error_sentinel' in decrypted_chunks: raise ValueError("RSA 解密失敗。")
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
        self.key, self.iv = key.encode('utf-8'), iv.encode('utf-8')

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
        self._server_public_key, self._client_private_key, self._aes_key_id, self._aes_key, self._aes_iv, self._login_token_id = (
                                                                                                                                 None,) * 6

    def _call_api(self, endpoint, payload, files=None, use_aes=True, skip_verification=False):
        print(f"\n--- 步驟: 呼叫 {endpoint} ---")
        json_payload = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
        if use_aes:
            if not all([self._aes_key, self._aes_iv, self._aes_key_id]): raise Exception("AES 金鑰尚未初始化…")
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
        if files:
            print(f"附加檔案: {list(files.keys())}")
            response = self.session.post(url, data={'EncData': enc_data}, files=files, headers=headers)
        else:
            response = self.session.post(url, data={'EncData': enc_data}, headers=headers)
        response.raise_for_status()
        response_content = response.text
        print(f"API 原始回應: {response_content}")
        response_signature = response.headers.get('X-iCP-Signature')
        if not skip_verification:
            self.rsa_helper.import_pem_public_key(self._server_public_key)
            if not self.rsa_helper.verify_sign_data_with_sha256(response_content, response_signature): raise Exception(
                f"{endpoint} 的回應簽章驗證失敗。")
            print("回應簽章驗證成功。")
        response_json = json.loads(response_content)
        if response_json.get('RtnCode') not in [1, 100001]:
            raise Exception(f"API 返回錯誤 (RtnCode {response_json.get('RtnCode')}): {response_json.get('RtnMsg')}")
        if 'EncData' in response_json and response_json['EncData']:
            if use_aes:
                decrypted_data_str = AesCryptoHelper(self._aes_key, self._aes_iv).decrypt(response_json['EncData'])
            else:
                self.rsa_helper.import_pem_private_key(self._client_private_key)
                decrypted_data_str = self.rsa_helper.decrypt(response_json['EncData'])
            print(f"回應 (已解密): {decrypted_data_str}")
            decrypted_json = json.loads(decrypted_data_str)
        else:
            decrypted_json = response_json
            print(f"回應 (無加密): {json.dumps(decrypted_json, ensure_ascii=False, indent=2)}")
        return decrypted_json, response_content, response_signature

    def _log_registration_data(self, data_to_log):
        try:
            os.makedirs(os.path.dirname(REGISTRATION_LOG_FILE), exist_ok=True)
            log_entry = (f"---\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                         f"UserCode: {data_to_log.get('UserCode', 'N/A')}\n"
                         f"CellPhone: {data_to_log.get('CellPhone', 'N/A')}\n"
                         f"Idno (ARC): {data_to_log.get('Idno', 'N/A')}\n---\n\n")
            with open(REGISTRATION_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print(f"\n✅ 註冊資料已成功記錄至: {REGISTRATION_LOG_FILE}")
        except Exception as e:
            print(f"\n❌ 錯誤: 無法將資料寫入記錄檔: {e}")

    def run_full_flow(self):
        reporter = HtmlReporter(report_title="iCashPay API 外國人註冊流程報告")
        current_step = "開始"
        log_data = {}
        try:
            current_step = "準備階段: 產生動態資料"
            random_suffix = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=4))
            common_device_info = {"AppName": "002", "DeviceID": f"b4f194a{random.randint(100000, 999999)}",
                                  "DeviceInfo": f"Pixel 7_{random_suffix}", "IsSimulator": "0", "OS": "2"}
            print(
                f"本次執行使用動態設備資訊: DeviceID={common_device_info['DeviceID']}, DeviceInfo={common_device_info['DeviceInfo']}")
            user_code = f"i{int(datetime.now().timestamp())}"
            cell_phone = get_next_phone_number()
            id_no = generate_final_valid_old_arc_id()
            user_pwd, confirm_sec_pwd = 'Aa123456', "246790"
            log_data.update({'UserCode': user_code, 'UserPwd': user_pwd, 'CellPhone': cell_phone, 'Idno': id_no,
                             'ConfirmSecPwd': confirm_sec_pwd, 'DeviceInfo': common_device_info})
            with open(LAST_IDNO_FILE, 'w') as f:
                f.write(id_no)
            print(f"動態資料已產生: UserCode={user_code}, CellPhone={cell_phone}, ARC No={id_no} (動態產生)")
            reporter.add_step(current_step, "✅ 成功", log_data)

            current_step = "金鑰交換流程"
            self._initialize_keys(reporter)

            current_step = "步驟 1: 設定註冊資訊 (SetRegisterInfo2022)"
            payload1 = {**common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'CellPhone': cell_phone, 'UserCode': user_code, 'UserPwd': user_pwd}
            result1, _, _ = self._call_api("app/MemberInfo/SetRegisterInfo2022", payload1)
            reporter.add_step(current_step, "✅ 成功", payload1, result1)
            self._login_token_id = result1.get("LoginTokenID")
            if not self._login_token_id: raise Exception("步驟 1 未能獲取 LoginTokenID。")
            with open(TOKEN_FILE, 'w') as f:
                f.write(self._login_token_id)
            print(f"LoginTokenID '{self._login_token_id}' 已儲存。")

            current_step = "步驟 2: 發送簡訊驗證碼 (SendAuthSMS)"
            payload2 = {**common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'CellPhone': cell_phone, 'LoginTokenID': self._login_token_id, 'SMSAuthType': '1',
                        'UserCode': ''}
            result2, _, _ = self._call_api("app/MemberInfo/SendAuthSMS", payload2)
            reporter.add_step(current_step, "✅ 成功", payload2, result2)
            auth_code = result2.get("AuthCode")
            if not auth_code: raise Exception("步驟 2 未能獲取 AuthCode。")
            with open(AUTH_CODE_FILE, 'w') as f:
                f.write(auth_code)
            print(f"AuthCode '{auth_code}' 已儲存。")

            current_step = "步驟 3: 驗證簡訊 (CheckRegisterAuthSMS)"
            payload3 = {**common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'CellPhone': cell_phone, 'LoginTokenID': self._login_token_id, 'AuthCode': auth_code}
            result3, _, _ = self._call_api("app/MemberInfo/CheckRegisterAuthSMS", payload3)
            reporter.add_step(current_step, "✅ 成功", payload3, result3)
            print("簡訊驗證成功。")

            current_step = "步驟 4: 外國人身分驗證 (AuthUniformID)"
            payload4 = {**common_device_info, "Timestamp": datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        "LoginTokenID": self._login_token_id, "CName": "外國人測試", "EnName": "JohnTest",
                        "Idno": id_no, "NationalityID": "1206", "BirthDay": "2000-01-01",
                        "UniformIssueDate": "2024-01-01", "UniformExpireDate": "", "UniformNumber": "F160000001",
                        "UniformPermanentType": True, "fileCols": "img1,img2"}
            img1_path, img2_path = os.path.join(BASE_PATH, 'img1.png'), os.path.join(BASE_PATH, 'img2.png')
            if not os.path.exists(img1_path): raise FileNotFoundError(f"找不到檔案: {img1_path}...")
            if not os.path.exists(img2_path): raise FileNotFoundError(f"找不到檔案: {img2_path}...")
            with open(img1_path, 'rb') as f1, open(img2_path, 'rb') as f2:
                files_for_upload = {'img1': ('img1.png', f1, 'image/png'), 'img2': ('img2.png', f2, 'image/png')}
                result4, _, _ = self._call_api("app/MemberInfo/AuthUniformID", payload4, files=files_for_upload)
            reporter.add_step(current_step, "✅ 成功", payload4, result4)
            print("身分驗證成功。")

            current_step = "步驟 5: 變更交易密碼 (ChangeSecurityPwd)"
            payload5 = {**common_device_info, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                        'ConfirmSecPwd': confirm_sec_pwd, 'NewSecPwd': confirm_sec_pwd}
            result5, _, _ = self._call_api("app/MemberInfo/ChangeSecurityPwd", payload5)
            reporter.add_step(current_step, "✅ 成功", payload5, result5)
            print("變更交易密碼成功。")

            log_data['LastTimestamp'] = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            self._log_registration_data(log_data)
            print("\n======= ✅ 外國人註冊流程 1-5 步驟執行成功！ ✅ =======")
        except Exception as e:
            print(f"\n======= ❌ 流程執行失敗於: {current_step} ❌ =======")
            print(f"錯誤訊息: {e}")
            error_info = f"Error: {e}\n\nTraceback:\n{traceback.format_exc()}"
            failed_payload = locals().get(f'payload{current_step[3].replace(":", "")}',
                                          None) if current_step.startswith("步驟") else log_data
            reporter.add_step(current_step, "❌ 失敗", failed_payload, error_details=error_info)
            print(f"====================================")
        finally:
            reporter.finalize_report()
            reporter.save_and_open_report(BASE_PATH)

    def _initialize_keys(self, reporter):
        print("--- 階段: 初始化金鑰 ---")
        url1 = f"{self.base_url}api/member/Certificate/GetDefaultPucCert"
        response1 = self.session.post(url1).json()
        if response1['RtnCode'] != 1: raise Exception("GetDefaultPucCert 失敗")
        default_cert_id, default_public_key = response1['DefaultPubCertID'], response1['DefaultPubCert']
        self._server_public_key = default_public_key
        reporter.add_step("金鑰交換 (1/3): GetDefaultPucCert", "✅ 成功", {"URL": url1}, response1)
        client_keys = self.rsa_helper.generate_pem_key()
        self._client_private_key = client_keys['private_key']
        client_pub_oneline = "".join(client_keys['public_key'].splitlines()[1:-1])
        payload2 = {'ClientPubCert': client_pub_oneline, 'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S"),
                    'CertID': default_cert_id, 'ServerPubKey': default_public_key}
        decrypted_result, raw_content, signature = self._call_api("api/member/Certificate/ExchangePucCert", payload2,
                                                                  use_aes=False, skip_verification=True)
        reporter.add_step("金鑰交換 (2/3): ExchangePucCert", "✅ 成功", payload2, decrypted_result)
        self._server_public_key = decrypted_result['ServerPubCert']
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(raw_content, signature): raise Exception(
            "ExchangePucCert 回應的手動簽章驗證失敗。")
        print("ExchangePucCert 回應手動簽章驗證成功。")
        server_pub_cert_id = decrypted_result['ServerPubCertID']
        payload3 = {'Timestamp': datetime.now().strftime("%Y/%m/%d %H:%M:%S")}
        json_payload3 = json.dumps(payload3, ensure_ascii=False)
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        enc_data3 = self.rsa_helper.encrypt(json_payload3)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        signature3 = self.rsa_helper.sign_data_with_sha256(enc_data3)
        headers3 = {'X-iCP-ServerPubCertID': str(server_pub_cert_id), 'X-iCP-Signature': signature3}
        url3 = f"{self.base_url}api/member/Certificate/GenerateAES"
        response3 = self.session.post(url3, data={'EncData': enc_data3}, headers=headers3)
        response3.raise_for_status()
        content3 = response3.text
        self.rsa_helper.import_pem_public_key(self._server_public_key)
        if not self.rsa_helper.verify_sign_data_with_sha256(content3,
                                                            response3.headers.get('X-iCP-Signature')): raise Exception(
            "GenerateAES 簽章驗證失敗")
        result3_enc = json.loads(content3)
        self.rsa_helper.import_pem_private_key(self._client_private_key)
        result3_dec = json.loads(self.rsa_helper.decrypt(result3_enc['EncData']))
        reporter.add_step("金鑰交換 (3/3): GenerateAES", "✅ 成功", payload3, result3_dec)
        self._aes_key_id, self._aes_key, self._aes_iv = result3_dec['EncKeyID'], result3_dec['AES_Key'], result3_dec[
            'AES_IV']
        print(f"金鑰初始化成功，AES KeyID: {self._aes_key_id}")


if __name__ == '__main__':
    print("--- 執行前檢查 ---")
    print(f"此腳本將會讀取位於 C:\\icppython 資料夾中的 img1.png 和 img2.png 檔案。")
    print("請確保這兩個檔案已經存在於該路徑下。")
    print("腳本將「動態產生」一個基於已知有效規則的舊式居留證號。")
    input("確認後請按 Enter 鍵繼續執行...")
    print("--------------------")

    api_client = FullFlowApiClient()
    api_client.run_full_flow()